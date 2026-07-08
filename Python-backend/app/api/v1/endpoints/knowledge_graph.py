from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field, field_validator
import json

from app.services.db.java_client import JavaBackendClient
from app.graph.knowledge_updater_graph import get_knowledge_updater_graph

router = APIRouter()
logger = logging.getLogger(__name__)
java_client = JavaBackendClient()

class AnalyzeRequest(BaseModel):
    user_id: int
    resource_ids: List[int]

class MasteryUpdateItem(BaseModel):
    """LLM 返回的单个节点掌握度更新"""
    node_id: str = Field(..., description="知识图谱节点 ID")
    new_mastery: float = Field(..., ge=0.0, le=1.0, description="新掌握度 0.0~1.0")

class UpdateMasteryRequest(BaseModel):
    user_id: int
    resource_id: int
    completed: bool

def _reanalyze_resources_task(user_id: int, resource_ids: List[int]):
    updater_graph = get_knowledge_updater_graph()
    
    for resource_id in resource_ids:
        try:
            logger.info(f"后台任务：开始重新分析资源 {resource_id}...")
            # 1. 获取资源信息
            resource = java_client.get_resource_by_id(resource_id)
            if not resource:
                logger.warning(f"后台任务：资源 {resource_id} 不存在")
                continue
            
            # 2. 从 module_data 中提取文本
            module_data = resource.get("moduleData", {})
            if isinstance(module_data, str):
                module_data = json.loads(module_data)
            
            resource_text = ""
            module_type = resource.get("moduleType", "")
            
            if module_type == "document":
                resource_text = module_data.get("content", "") or module_data.get("markdown", "")
            elif module_type == "quiz":
                questions = module_data.get("questions", [])
                resource_text = json.dumps(questions, ensure_ascii=False)
            elif module_type == "summary":
                resource_text = module_data.get("content", "")
            else:
                # 通用回退提取
                resource_text = json.dumps(module_data, ensure_ascii=False)

            if not resource_text or len(str(resource_text)) < 10:
                logger.warning(f"后台任务：资源 {resource_id} 文本太短或提取失败，跳过分析")
                continue

            # 3. 构造 state 并调用图更新
            updater_state = {
                "user_id": user_id,
                "resource_id": resource_id,
                "resource_text": str(resource_text)[:10000] # 防止单次文本过长打爆上下文
            }
            
            updater_graph.invoke(updater_state)
            logger.info(f"后台任务：资源 {resource_id} 分析完成")
            
        except Exception as e:
            logger.error(f"后台任务：重新分析资源 {resource_id} 失败: {e}")

@router.post("/knowledge-graph/analyze")
async def analyze_resources(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    触发对所选资源的重新图谱分析。
    采用异步后台任务防止客户端阻塞。
    """
    if not payload.user_id or not payload.resource_ids:
        raise HTTPException(status_code=400, detail="Missing user_id or resource_ids")
        
    background_tasks.add_task(_reanalyze_resources_task, payload.user_id, payload.resource_ids)
    
    return {"code": 200, "message": "分析任务已投递后台", "data": True}


class OptimizeRequest(BaseModel):
    domain_id: int
    instruction: str

from fastapi.responses import StreamingResponse
import asyncio
from app.agents.graph_optimizer import optimize_graph

def _update_mastery_task(user_id: int, resource_id: int, completed: bool):
    """后台任务：LLM 分析资源完成状态，更新相关知识图谱节点的掌握度"""
    action_str = "完成" if completed else "取消完成"
    logger.info(f"[掌握度更新] 开始分析: user={user_id}, resource={resource_id}, action={action_str}")
    try:
        from app.agents.llm_factory import get_knowledge_updater_llm

        # 1. 获取资源内容
        resource = java_client.get_resource_by_id(resource_id)
        if not resource:
            logger.warning(f"[掌握度更新] 资源 {resource_id} 不存在")
            return
        logger.info(f"[掌握度更新] 获取资源成功: {resource.get('title', '')[:50]}")

        module_data = resource.get("moduleData", {})
        if isinstance(module_data, str):
            try:
                module_data = json.loads(module_data)
            except Exception:
                module_data = {}

        resource_title = resource.get("title", "")
        resource_content = module_data.get("content", "") or module_data.get("markdown", "") or ""
        if not resource_content:
            resource_content = json.dumps(module_data, ensure_ascii=False)[:3000]

        # 2. 获取用户所有领域图谱
        domains = java_client.get_user_knowledge_domains(user_id)
        if not domains:
            logger.info(f"[掌握度更新] 用户 {user_id} 无知识图谱领域")
            return

        # 3. 遍历领域，找到包含该资源的节点
        updates = []  # [(domain_id, node_id, new_mastery)]
        logger.info(f"[掌握度更新] 扫描 {len(domains)} 个领域，查找关联节点...")

        for domain in domains:
            domain_id = domain.get("id")
            graph_data = domain.get("graphData", {})
            if isinstance(graph_data, str):
                try:
                    graph_data = json.loads(graph_data)
                except Exception:
                    continue

            nodes = graph_data.get("nodes", [])
            linked_nodes = [n for n in nodes if resource_id in (n.get("resource_ids") or [])]
            if not linked_nodes:
                continue

            domain_name = domain.get("domainName", "未知领域")
            logger.info(f"[掌握度更新] 领域「{domain_name}」找到 {len(linked_nodes)} 个关联节点，开始 LLM 分析...")

            # 4. LLM 分析：根据资源内容和完成状态，决定每个节点的新掌握度
            llm = get_knowledge_updater_llm()

            nodes_info = []
            for n in linked_nodes:
                nodes_info.append({
                    "node_id": n.get("id"),
                    "name": n.get("name", ""),
                    "description": n.get("description", ""),
                    "current_mastery": n.get("mastery_level", 0.0),
                })

            action = "用户已完成学习该资源" if completed else "用户取消了该资源的完成标记（之前学过但现在标记为未完成）"

            # 提取更有代表性的内容（取前3000字 + 后1000字，覆盖开头和结尾）
            content_for_llm = resource_content[:3000]
            if len(resource_content) > 4000:
                content_for_llm += "\n...\n" + resource_content[-1000:]

            prompt = f"""你是一个学习分析专家。用户在学习领域「{domain_name}」中，有一份学习资源的状态发生了变化。

资源标题：{resource_title}
资源内容：
{content_for_llm}

状态变化：{action}

以下知识图谱节点与该资源直接关联（每个节点的 resource_ids 中包含该资源的 ID）：
{json.dumps(nodes_info, ensure_ascii=False, indent=2)}

请为**每一个**关联节点决定新的掌握度（mastery_level，0.0~1.0）。

【规则】
- **返回所有关联节点**，尽量评估和更新所有和资源内容牵涉到的节点。
- 如果用户**完成**了资源：
  - 资源内容中明确讲解了该节点概念 → 提升到 0.5~0.8
  - 资源内容中提到了该节点但未深入讲解 → 提升到 0.3~0.5
  - 资源内容中只是顺带提及 → 提升到 0.1~0.3
  - 不要直接设为 1.0（还需要实践和复习巩固）
- 如果用户**取消完成**：适当降低掌握度，降低 0.1~0.3，但不要直接降到 0（可能通过其他资源学过）。
- 掌握度范围：0.0 ~ 1.0，最终值必须在范围内。
- 新掌握度应该 >= 当前掌握度（完成时只升不降），或者 <= 当前掌握度（取消时只降不升）。

【输出格式】严格输出 JSON 数组，每个关联节点都必须包含：
[{{"node_id": "xxx", "new_mastery": 0.6}}, {{"node_id": "yyy", "new_mastery": 0.4}}, ...]

只输出 JSON，不要其他文本。"""

            try:
                result = llm.chat_json([{"role": "user", "content": prompt}])
                # Pydantic 校验 LLM 返回值
                raw_items = result if isinstance(result, list) else [result] if isinstance(result, dict) else []
                for item in raw_items:
                    try:
                        validated = MasteryUpdateItem.model_validate(item)
                        updates.append((domain_id, validated.node_id, validated.new_mastery))
                    except Exception as ve:
                        logger.warning(f"[掌握度更新] Pydantic 校验跳过: {ve}")
            except Exception as e:
                logger.error(f"[掌握度更新] LLM 分析失败 domain={domain_id}: {e}")

        # 5. 批量更新节点掌握度
        for domain_id, node_id, new_mastery in updates:
            try:
                java_client.patch_knowledge_graph_node(domain_id, node_id, mastery_level=new_mastery)
                logger.info(f"[掌握度更新] domain={domain_id} node={node_id} mastery={new_mastery}")
            except Exception as e:
                logger.error(f"[掌握度更新] 更新失败 domain={domain_id} node={node_id}: {e}")

        logger.info(f"[掌握度更新] 完成: resource={resource_id} completed={completed} updates={len(updates)}")

    except Exception as e:
        logger.error(f"[掌握度更新] 任务异常: {e}", exc_info=True)


@router.post("/knowledge-graph/update-mastery")
async def update_mastery(payload: UpdateMasteryRequest, background_tasks: BackgroundTasks):
    """
    资源完成状态变更后，异步触发 LLM 分析并更新知识图谱节点掌握度
    """
    if not payload.user_id or not payload.resource_id:
        raise HTTPException(status_code=400, detail="Missing user_id or resource_id")

    background_tasks.add_task(_update_mastery_task, payload.user_id, payload.resource_id, payload.completed)
    return {"code": 200, "message": "掌握度分析已投递后台", "data": True}


class UpdateMasteryBatchRequest(BaseModel):
    user_id: int
    resource_ids: List[int]
    completed: bool


def _update_mastery_batch_task(user_id: int, resource_ids: List[int], completed: bool):
    """批量掌握度分析：串行处理，避免并发冲突和 429 限流"""
    logger.info(f"[掌握度更新-批量] 开始: user={user_id}, resources={len(resource_ids)}, completed={completed}")
    for i, resource_id in enumerate(resource_ids):
        try:
            logger.info(f"[掌握度更新-批量] ({i+1}/{len(resource_ids)}) 处理 resource={resource_id}")
            _update_mastery_task(user_id, resource_id, completed)
        except Exception as e:
            logger.error(f"[掌握度更新-批量] resource={resource_id} 失败: {e}")
    logger.info(f"[掌握度更新-批量] 全部完成: {len(resource_ids)} 个资源")


@router.post("/knowledge-graph/update-mastery-batch")
async def update_mastery_batch(payload: UpdateMasteryBatchRequest, background_tasks: BackgroundTasks):
    """
    批量掌握度分析：串行处理多个资源，避免并发冲突和 LLM 429 限流
    """
    if not payload.user_id or not payload.resource_ids:
        raise HTTPException(status_code=400, detail="Missing user_id or resource_ids")

    background_tasks.add_task(_update_mastery_batch_task, payload.user_id, payload.resource_ids, payload.completed)
    return {"code": 200, "message": f"批量掌握度分析已投后台（{len(payload.resource_ids)} 个资源）", "data": True}


@router.post("/knowledge-graph/optimize")
async def optimize_knowledge_graph(payload: OptimizeRequest):
    """
    智能整理图谱 (SSE流式返回状态)
    """
    if not payload.domain_id or not payload.instruction:
        raise HTTPException(status_code=400, detail="Missing domain_id or instruction")

    async def generate():
        try:
            yield f'data: {json.dumps({"type": "progress", "message": "正在连接知识图谱架构师..."}, ensure_ascii=False)}\n\n'
            await asyncio.sleep(0.5)
            
            # 获取当前完整图谱
            yield f'data: {json.dumps({"type": "progress", "message": "正在提取全量图谱结构..."}, ensure_ascii=False)}\n\n'
            domain_data = java_client.get_domain_knowledge_graph(payload.domain_id)
            if not domain_data:
                yield f'data: {json.dumps({"type": "error", "message": "无法获取知识领域数据"}, ensure_ascii=False)}\n\n'
                return
            
            domain_name = domain_data.get("domainName", "未知领域")
            current_graph = domain_data.get("graphData", {"nodes": [], "edges": []})
            if isinstance(current_graph, str):
                current_graph = json.loads(current_graph)
                
            node_count = len(current_graph.get("nodes", []))
            yield f'data: {json.dumps({"type": "progress", "message": f"提取成功，共 {node_count} 个节点。正在执行大模型重构规划..."}, ensure_ascii=False)}\n\n'
            
            # 由于大模型调用可能比较耗时，我们把它放到线程池里执行，避免阻塞主事件循环
            loop = asyncio.get_event_loop()
            new_graph = await loop.run_in_executor(None, optimize_graph, current_graph, payload.instruction, domain_name)
            
            yield f'data: {json.dumps({"type": "progress", "message": "规划完成，正在将新架构持久化至数据库..."}, ensure_ascii=False)}\n\n'
            
            # 保存到数据库
            java_client.update_knowledge_domain(payload.domain_id, graph_data=new_graph)
            
            # 返回成功和新的图谱数据
            yield f'data: {json.dumps({"type": "done", "graphData": new_graph}, ensure_ascii=False)}\n\n'
            
        except Exception as e:
            logger.error(f"图谱整理失败: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")

