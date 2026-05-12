"""
内容编排智能体 - 将 RAG 检索结果规划排版为模块化的顺序合理、排版美观的多模态学习资源
采用 mimo-v2.5 标准模型（唯一使用标准模型的智能体）

优化策略：
- 支持并行编排模式：为每个模块并发调用 LLM 生成内容
- 支持批量编排模式：一次性生成所有模块（原有模式）
- 默认使用并行模式，提升性能和可靠性
"""
import logging
import asyncio
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_content_orchestrator_llm

logger = logging.getLogger("agents.content_orchestrator")

SYSTEM_PROMPT_BATCH = """你是一个专业的内容编排专家。你的任务是将检索到的多模态知识内容，按照合理美观的顺序和模块化结构编排为学习资源。

## 编排要求
1. 按照逻辑顺序组织内容模块，由浅入深
2. 每个模块结构清晰，标题层次分明
3. 图片资源要附带说明注解，使用 Markdown 图片格式
4. 代码块要标注语言类型
5. 重要概念用加粗或引用格式标注
6. 模块间要有合理的过渡说明

## 输出格式
严格输出 JSON：
{
  "title": "学习资源总标题",
  "description": "简要描述",
  "modules": [
    {
      "module_order": 1,
      "module_type": "text",
      "title": "模块标题",
      "content": "模块内容（Markdown格式）",
      "metadata": {
        "key_concepts": ["概念1", "概念2"],
        "has_images": true,
        "has_code": false,
        "estimated_read_time": "5分钟"
      }
    }
  ],
  "total_modules": 5,
  "summary": "学习资源总结"
}

## module_type 取值
- text: 文本内容
- image: 图片说明
- diagram: 流程图/思维导图描述
- code: 代码示例（含完整注释和运行说明，使用带语言标签的代码块）
- summary: 总结回顾（提炼核心要点，适合快速复习）
- mindmap: 思维导图（使用 Markdown 缩进列表或 Mermaid mindmap 语法表示层级关系）

## 规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 图片使用 Markdown 格式: ![描述](URL)
- 内容要完整充实，不要过于简略
- 模块标题必须是实际内容名称，严禁使用「第一章」「第二章」「模块一」「Part 1」等章节编号前缀，也不要使用「XXX:」等冒号后缀。标题只写实际内容名即可
- 严禁生成 quiz（题目/练习题）类型的模块！题目只能由专门的题目生成智能体单独生成，编排智能体不允许产出任何题目内容"""


SYSTEM_PROMPT_PARALLEL = """你是一个专业的内容编排专家。你的任务是为单个学习模块编排生成高质量的学习内容。

## 编排要求
1. 内容结构清晰，标题层次分明
2. 图片资源要附带说明注解，使用 Markdown 图片格式
3. 代码块要标注语言类型
4. 重要概念用加粗或引用格式标注
5. 内容要完整充实，适合独立学习

## 输出格式
严格输出 JSON，确保所有字符串字段中的特殊字符（引号、换行符、反斜杠等）都正确转义：
{
  "module_type": "text",
  "title": "模块标题",
  "content": "模块内容（Markdown格式，换行符必须转义为\\n）",
  "description": "模块简要描述（单行文本）",
  "metadata": {
    "key_concepts": ["概念1", "概念2"],
    "has_images": true,
    "has_code": false,
    "estimated_read_time": "5分钟"
  }
}

## module_type 取值
- text: 文本内容
- image: 图片说明
- diagram: 流程图/思维导图描述
- code: 代码示例（含完整注释和运行说明，使用带语言标签的代码块）
- summary: 总结回顾（提炼核心要点，适合快速复习）
- mindmap: 思维导图（使用 Markdown 缩进列表或 Mermaid mindmap 语法表示层级关系）

## JSON 格式规则
- content 字段中的所有换行符必须转义为 \\n
- 所有字符串中的双引号必须转义为 \"
- 所有字符串中的反斜杠必须转义为 \\\\
- description 字段必须是单行文本
- 确保输出的是合法的 JSON 格式

## 内容规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 图片使用 Markdown 格式: ![描述](URL)
- 内容要完整充实，不要过于简略
- 模块标题必须是实际内容名称，严禁使用「第一章」「第二章」「模块一」等章节编号前缀
- 严禁生成 quiz（题目/练习题）类型的模块！"""

def _generate_single_module(
    module_info: Dict[str, Any],
    module_order: int,
    rag_chunks: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
    learning_goal: str,
    chat_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    为单个模块生成内容（用于并行编排）
    
    Args:
        module_info: 模块信息（来自任务分解）
        module_order: 模块顺序
        rag_chunks: RAG 检索到的内容块
        user_profile: 用户画像
        learning_goal: 学习目标
        chat_history: 对话历史
    
    Returns:
        生成的模块内容
    """
    llm = get_content_orchestrator_llm()
    
    module_title = module_info.get("title", "")
    module_desc = module_info.get("description", "")
    key_points = module_info.get("key_points", [])
    
    # 筛选与该模块相关的 RAG 内容
    relevant_chunks = []
    for chunk in rag_chunks:
        chunk_content = chunk.get("content", "").lower()
        doc_title = chunk.get("doc_title", "").lower()
        heading = " ".join(chunk.get("heading", [])).lower()
        
        # 简单的相关性判断：标题或关键点在内容中出现
        is_relevant = (
            module_title.lower() in chunk_content or
            module_title.lower() in doc_title or
            module_title.lower() in heading or
            any(kp.lower() in chunk_content for kp in key_points)
        )
        
        if is_relevant:
            relevant_chunks.append(chunk)
    
    # 如果没有相关内容，使用前 5 个通用内容
    if not relevant_chunks:
        relevant_chunks = rag_chunks[:5]
    
    # 构造内容摘要
    content_parts = []
    for i, chunk in enumerate(relevant_chunks[:10]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_parts.append(
                f"[资料{i+1}] [图片] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"图片URL: {chunk.get('image_path', '')}\n"
                f"AI描述: {chunk.get('image_caption', '')}\n"
                f"上下文: {chunk.get('content', '')}"
            )
        else:
            content_parts.append(
                f"[资料{i+1}] [文本] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"内容: {chunk.get('content', '')}"
            )
    
    content_text = "\n\n---\n\n".join(content_parts)
    
    # 用户偏好
    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    vv = fs.get("visual_verbal", 0)
    pref_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")
    
    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-4:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:150]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_PARALLEL},
        {"role": "user", "content": f"""学习目标: {learning_goal}

对话历史:
{history_text if history_text else "无历史记录"}

当前模块信息:
- 标题: {module_title}
- 描述: {module_desc}
- 关键要点: {', '.join(key_points)}
- 模块顺序: 第 {module_order} 个模块

用户内容偏好: {pref_text}

检索到的相关知识资料:
{content_text}

请为该模块生成高质量的学习内容，输出 JSON:"""}
    ]
    
    try:
        result = llm.chat_json(messages, max_tokens=4096)
        result["module_order"] = module_order
        result["module_id"] = module_info.get("module_id", module_order)
        return result
    except Exception as e:
        logger.error(f"  [模块{module_order}] 生成失败: {str(e)}")
        return {
            "module_order": module_order,
            "module_id": module_info.get("module_id", module_order),
            "module_type": "text",
            "title": module_title,
            "content": f"内容生成失败: {str(e)}",
            "description": module_desc,
            "metadata": {"error": str(e)},
        }


def content_orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """
    内容编排智能体节点
    
    支持两种模式：
    1. 并行模式（默认）：为每个模块并发调用 LLM 生成内容
    2. 批量模式：一次性生成所有模块（原有模式）
    
    支持重试模式：
    - 只重新生成未通过审查的模块
    - 保留已通过审查的模块
    - 合并新旧模块结果
    
    并行模式优势：
    - 更快的响应速度（并发执行）
    - 更好的容错性（单个模块失败不影响其他）
    - 更好的流式体验（逐个模块实时输出）
    - 无 token 限制（每个模块独立生成）
    """
    rag_chunks = state.get("rag_context_chunks", [])
    task_breakdown = state.get("task_breakdown", {})
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    user_profile = state.get("user_profile", {})
    generated_content = state.get("generated_content")
    chat_history = state.get("chat_history", [])
    
    # 是否使用并行模式（默认开启）
    use_parallel = state.get("use_parallel_orchestration", True)
    
    # 检查是否为重试模式（只重新生成指定模块）
    retry_mode = state.get("retry_mode", False)
    target_module_ids = state.get("target_module_ids", [])
    existing_modules = state.get("module_list", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [内容编排智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    logger.info(f"  输入内容块: {len(rag_chunks)} 个")
    logger.info(f"  自主生成内容: {'有' if generated_content else '无'}")
    logger.info(f"  编排模式: {'并行' if use_parallel else '批量'}")
    
    modules = task_breakdown.get("modules", []) if task_breakdown else []
    
    # 重试模式：只重新生成未通过的模块
    if retry_mode and target_module_ids and existing_modules:
        logger.info(f"  [内容编排智能体] 🔄 重试模式：只重新生成模块 {target_module_ids}")
        logger.info(f"  [内容编排智能体] 保留已通过的 {len(existing_modules) - len(target_module_ids)} 个模块")
        
        # 筛选出需要重新生成的模块信息
        target_modules_info = []
        for module_id in target_module_ids:
            if 1 <= module_id <= len(modules):
                module_info = modules[module_id - 1]
                target_modules_info.append((module_id, module_info))
        
        if not target_modules_info:
            logger.warning(f"  [内容编排智能体] 未找到目标模块信息，跳过重试")
            return {
                "retry_mode": False,
                "target_module_ids": [],
                "current_step": "内容编排智能体: 未找到目标模块，跳过重试",
            }
        
        # 如果有自主生成内容，添加到 RAG 结果中
        if generated_content:
            rag_chunks = list(rag_chunks)
            rag_chunks.append({
                "type": "text",
                "content": generated_content.get("content", ""),
                "doc_title": "自主生成内容",
                "heading": [generated_content.get("title", "补充内容")],
            })
        
        # 并发重新生成未通过的模块
        async def run_retry_orchestration():
            """并发重新生成未通过的模块"""
            loop = asyncio.get_event_loop()
            
            tasks = []
            for module_id, module_info in target_modules_info:
                task = loop.run_in_executor(
                    None,
                    _generate_single_module,
                    module_info,
                    module_id,
                    rag_chunks,
                    user_profile,
                    learning_goal,
                    chat_history,
                )
                tasks.append(task)
            
            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            new_module_results = loop.run_until_complete(run_retry_orchestration())
            loop.close()
            
            # 处理异常结果
            new_modules = []
            for i, result in enumerate(new_module_results):
                module_id = target_modules_info[i][0]
                if isinstance(result, Exception):
                    logger.error(f"  [模块{module_id}] 重新生成异常: {str(result)}")
                    # 保留原有模块
                    original_module = existing_modules[module_id - 1] if module_id <= len(existing_modules) else None
                    if original_module:
                        new_modules.append(original_module)
                else:
                    new_modules.append(result)
            
            # 合并结果：保留通过的模块，替换未通过的模块
            final_modules = _merge_modules(existing_modules, new_modules, target_module_ids)
            
            # 按 module_order 排序
            final_modules.sort(key=lambda x: x.get("module_order", 0))
            
            # 构造完整结果
            orchestrated_content = {
                "title": task_breakdown.get("title", learning_goal),
                "description": task_breakdown.get("description", ""),
                "modules": final_modules,
                "total_modules": len(final_modules),
                "summary": f"已重新生成 {len(new_modules)} 个模块，保留 {len(final_modules) - len(new_modules)} 个模块",
            }
            
            logger.info(f"  [内容编排智能体] 重试编排完成!")
            logger.info(f"    重新生成: {len(new_modules)} 个模块")
            logger.info(f"    保留原有: {len(final_modules) - len(new_modules)} 个模块")
            logger.info(f"    总模块数: {len(final_modules)}")
            for i, m in enumerate(final_modules):
                mtype = m.get("module_type", "text")
                mtitle = m.get("title", "")
                module_order = m.get("module_order", i + 1)
                is_new = module_order in target_module_ids
                status = " 重新生成" if is_new else " 保留"
                logger.info(f"      模块{module_order} [{mtype}] {status}: {mtitle}")
            logger.info(f"{'='*60}")
            
            return {
                "orchestrated_content": orchestrated_content,
                "module_list": final_modules,
                "retry_mode": False,  # 清除重试标记
                "target_module_ids": [],
                "current_step": f"内容编排智能体: 重试编排完成，重新生成 {len(new_modules)} 个模块",
                "stream_events": [{
                    "event_type": "module",
                    "agent": "content_orchestrator",
                    "data": orchestrated_content,
                    "step_description": f"重试编排完成，重新生成 {len(new_modules)} 个模块"
                }],
            }
            
        except Exception as e:
            logger.error(f"  [内容编排智能体] 重试编排失败: {str(e)}")
            # 保留原有模块
            return {
                "retry_mode": False,
                "target_module_ids": [],
                "error": f"重试编排失败: {str(e)}",
                "current_step": f"内容编排智能体: 重试编排失败 - {str(e)}",
            }
    
    # 如果有自主生成内容，添加到 RAG 结果中
    if generated_content:
        rag_chunks = list(rag_chunks)
        rag_chunks.append({
            "type": "text",
            "content": generated_content.get("content", ""),
            "doc_title": "自主生成内容",
            "heading": [generated_content.get("title", "补充内容")],
        })
    
    # 并行模式：为每个模块并发生成内容
    if use_parallel and modules:
        logger.info(f"  [内容编排智能体] 使用并行模式，共 {len(modules)} 个模块")
        
        async def run_parallel_orchestration():
            """并发为每个模块生成内容"""
            loop = asyncio.get_event_loop()
            
            tasks = []
            for i, module in enumerate(modules):
                task = loop.run_in_executor(
                    None,
                    _generate_single_module,
                    module,
                    i + 1,
                    rag_chunks,
                    user_profile,
                    learning_goal,
                    chat_history,
                )
                tasks.append(task)
            
            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            module_results = loop.run_until_complete(run_parallel_orchestration())
            loop.close()
            
            # 处理异常结果
            modules_list = []
            for i, result in enumerate(module_results):
                if isinstance(result, Exception):
                    logger.error(f"  [模块{i+1}] 生成异常: {str(result)}")
                    modules_list.append({
                        "module_order": i + 1,
                        "module_type": "text",
                        "title": modules[i].get("title", f"模块 {i+1}"),
                        "content": f"内容生成失败: {str(result)}",
                        "metadata": {"error": str(result)},
                    })
                else:
                    modules_list.append(result)
            
            # 按 module_order 排序
            modules_list.sort(key=lambda x: x.get("module_order", 0))
            
            # 构造完整结果
            orchestrated_content = {
                "title": task_breakdown.get("title", learning_goal),
                "description": task_breakdown.get("description", ""),
                "modules": modules_list,
                "total_modules": len(modules_list),
                "summary": f"已生成 {len(modules_list)} 个学习模块",
            }
            
            logger.info(f"  [内容编排智能体] 并行编排完成!")
            logger.info(f"    标题: {orchestrated_content.get('title', '未命名')}")
            logger.info(f"    模块数: {len(modules_list)}")
            for i, m in enumerate(modules_list):
                mtype = m.get("module_type", "text")
                mtitle = m.get("title", "")
                concepts = m.get("metadata", {}).get("key_concepts", [])
                has_error = "error" in m.get("metadata", {})
                status = " 失败" if has_error else " 成功"
                logger.info(f"      模块{i+1} [{mtype}] {status}: {mtitle} (概念: {', '.join(concepts[:3])})")
            logger.info(f"{'='*60}")
            
            return {
                "orchestrated_content": orchestrated_content,
                "module_list": modules_list,
                "current_step": f"内容编排智能体: 并行编排完成，共 {len(modules_list)} 个模块",
                "stream_events": [{
                    "event_type": "module",
                    "agent": "content_orchestrator",
                    "data": orchestrated_content,
                    "step_description": f"并行编排完成，共 {len(modules_list)} 个模块"
                }],
            }
            
        except Exception as e:
            logger.error(f"  [内容编排智能体] 并行编排失败: {str(e)}")
            # 降级到批量模式
            logger.warning(f"  [内容编排智能体] 降级到批量模式")
            use_parallel = False
    
    # 批量模式：一次性生成所有模块（原有逻辑）
    if not use_parallel or not modules:
        logger.info(f"  [内容编排智能体] 使用批量模式")
        return _batch_orchestration(
            rag_chunks, task_breakdown, user_message, learning_goal,
            user_profile, generated_content, chat_history
        )


def _batch_orchestration(
    rag_chunks: List[Dict[str, Any]],
    task_breakdown: Dict[str, Any],
    user_message: str,
    learning_goal: str,
    user_profile: Dict[str, Any],
    generated_content: Dict[str, Any],
    chat_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """批量编排模式：一次性生成所有模块（原有逻辑）"""
def _batch_orchestration(
    rag_chunks: List[Dict[str, Any]],
    task_breakdown: Dict[str, Any],
    user_message: str,
    learning_goal: str,
    user_profile: Dict[str, Any],
    generated_content: Dict[str, Any],
    chat_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """批量编排模式：一次性生成所有模块（原有逻辑）"""
    llm = get_content_orchestrator_llm()

    content_parts = []
    for i, chunk in enumerate(rag_chunks[:20]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_parts.append(
                f"[资料{i+1}] [图片] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"图片URL: {chunk.get('image_path', '')}\n"
                f"AI描述: {chunk.get('image_caption', '')}\n"
                f"上下文: {chunk.get('content', '')}"
            )
        else:
            content_parts.append(
                f"[资料{i+1}] [文本] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"内容: {chunk.get('content', '')}"
            )

    content_text = "\n\n---\n\n".join(content_parts)

    generated_text = ""
    if generated_content:
        generated_text = f"\n\n## 自主生成的补充内容:\n{generated_content.get('content', '')}"

    modules_desc = ""
    if task_breakdown:
        modules = task_breakdown.get("modules", [])
        modules_desc = "\n".join([
            f"- 模块{m.get('module_id', i+1)}: {m.get('title', '')} - {m.get('description', '')}"
            for i, m in enumerate(modules)
        ])

    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    vv = fs.get("visual_verbal", 0)
    pref_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")

    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-6:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_BATCH},
        {"role": "user", "content": f"""学习目标: {learning_goal}

对话历史（请结合上下文理解用户需求）:
{history_text if history_text else "无历史记录"}

参考学习路径:
{modules_desc}

用户内容偏好: {pref_text}

检索到的知识资料:
{content_text}
{generated_text}

请将以上资料编排为结构化的学习资源，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [内容编排智能体] 正在调用 LLM 进行批量编排...")
        result = llm.chat_json(messages, max_tokens=8192)
        modules_list = result.get("modules", [])

        logger.info(f"  [内容编排智能体] 批量编排完成!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    模块数: {len(modules_list)}")
        for i, m in enumerate(modules_list):
            mtype = m.get("module_type", "text")
            mtitle = m.get("title", "")
            concepts = m.get("metadata", {}).get("key_concepts", [])
            logger.info(f"      模块{i+1} [{mtype}]: {mtitle} (概念: {', '.join(concepts[:3])})")
        logger.info(f"{'='*60}")

        return {
            "orchestrated_content": result,
            "module_list": modules_list,
            "current_step": f"内容编排智能体: 批量编排完成，共 {len(modules_list)} 个模块",
            "stream_events": [{
                "event_type": "module",
                "agent": "content_orchestrator",
                "data": result,
                "step_description": f"批量编排完成，共 {len(modules_list)} 个模块"
            }],
        }

    except Exception as e:
        logger.error(f"  [内容编排智能体] 批量编排失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"内容编排失败: {str(e)}",
            "current_step": f"内容编排智能体: 编排失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "content_orchestrator",
                "data": {"error": str(e)},
                "step_description": "内容编排失败"
            }],
        }


def _merge_modules(
    existing_modules: List[Dict[str, Any]],
    new_modules: List[Dict[str, Any]],
    target_module_ids: List[int],
) -> List[Dict[str, Any]]:
    """
    合并模块结果：保留通过的模块，替换未通过的模块
    
    Args:
        existing_modules: 原有的所有模块
        new_modules: 新生成的模块（只包含需要替换的）
        target_module_ids: 需要替换的模块编号列表
    
    Returns:
        合并后的完整模块列表
    """
    # 创建新模块的映射表（module_order -> module）
    new_modules_map = {}
    for module in new_modules:
        module_order = module.get("module_order", 0)
        new_modules_map[module_order] = module
    
    # 合并结果
    final_modules = []
    for i, existing_module in enumerate(existing_modules):
        module_order = existing_module.get("module_order", i + 1)
        
        # 如果该模块需要替换且有新生成的版本，使用新版本
        if module_order in target_module_ids and module_order in new_modules_map:
            final_modules.append(new_modules_map[module_order])
            logger.info(f"    [合并] 模块{module_order}: 使用新生成版本")
        else:
            # 否则保留原有版本
            final_modules.append(existing_module)
            logger.info(f"    [合并] 模块{module_order}: 保留原有版本")
    
    return final_modules
