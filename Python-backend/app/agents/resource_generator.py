"""
多模态资源自主生成智能体 - 结合 Tavily 网络搜索自主生成高质量学习内容
支持并行生成多个模块
"""
import logging
import json
import asyncio
import concurrent.futures
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_generator_llm
from app.agents.search_utils import search_tavily, execute_searches
from app.prompts import RESOURCE_GENERATOR_PROMPT, SEARCH_PLANNING_PROMPT
from app.core.config import settings
from app.utils.token_recorder import record_from_mimo


def _emit(state: dict, event_type: str, content: str):
    """通过 sse_callback 实时推送 SSE 事件"""
    cb = state.get("sse_callback")
    if cb:
        try:
            cb(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass

logger = logging.getLogger("agents.resource_generator")


def _format_search_results(results: List[Dict[str, str]]) -> str:
    """格式化搜索结果为 LLM 可读文本（带编号，供正文引用）"""
    lines = []
    for i, r in enumerate(results):
        title = r.get("title", "无标题")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        line = f"[{i + 1}] {title}\n    {snippet}"
        if url:
            line += f"\n    来源: {url}"
        lines.append(line)
    return "\n".join(lines)


def _format_image_results(images: List[Dict[str, str]], max_images: int = 6) -> str:
    """格式化图片列表为 LLM 可读文本，供 LLM 选择最相关的嵌入正文"""
    if not images:
        return ""
    lines = []
    for i, img in enumerate(images[:max_images]):
        desc = img.get("description", "") or "相关图片"
        url = img.get("url", "")
        if url:
            lines.append(f"[img{i + 1}] {desc}\n    URL: {url}")
    return "\n".join(lines)


def _summarize_existing_results(results: List[Dict[str, str]], max_items: int = 15) -> str:
    """简要摘要已有搜索结果，供 LLM 判断是否需要补充搜索"""
    if not results:
        return "暂无搜索结果"
    lines = []
    for r in results[:max_items]:
        title = r.get("title", "无标题")[:80]
        snippet = r.get("snippet", "")[:100]
        lines.append(f"  {title} | {snippet}")
    header = f"已收集 {len(results)} 条结果（以下展示前 {min(len(results), max_items)} 条）:\n"
    return header + "\n".join(lines)


# ==================== 单模块生成 ====================

def _generate_single_module(
    module_info: Dict[str, Any],
    module_order: int,
    learning_goal: str,
    user_profile: Dict[str, Any],
    sse_callback=None,
    resource_id: int = 0,
) -> Dict[str, Any]:
    """
    为单个模块执行搜索 + 内容生成流程

    Args:
        module_info: 模块信息 {title, description, resources, ...}
        module_order: 模块序号
        learning_goal: 学习目标
        user_profile: 用户画像
        sse_callback: SSE 回调
        resource_id: 占位资源 ID（用于流式输出标识）
    """
    llm = get_resource_generator_llm()
    module_title = module_info.get("title", f"模块 {module_order}")
    module_desc = module_info.get("description", "")
    topic = f"{module_title}: {module_desc}" if module_desc else module_title
    # 将学习目标作为上下文前缀，确保搜索查询不丢失原始主题限定词
    if learning_goal and learning_goal not in topic:
        topic = f"{learning_goal} - {topic}"

    logger.info(f"  [资源生成] 模块{module_order} 开始: {module_title}")

    # 用户画像风格提示
    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    style_hints = []
    if fs.get("visual_verbal", 0) < -0.3:
        style_hints.append("多使用图表、流程图描述")
    if fs.get("sensing_intuitive", 0) < -0.3:
        style_hints.append("多给出具体实例和实际案例")
    if fs.get("sequential_global", 0) < -0.3:
        style_hints.append("按照步骤顺序逐步讲解")
    style_text = "用户偏好: " + "; ".join(style_hints) if style_hints else ""

    # ==================== 多轮搜索 ====================
    search_context = ""
    search_result_count = 0
    all_search_results: List[Dict[str, str]] = []
    all_images: List[Dict[str, str]] = []
    MAX_SEARCH_ROUNDS = 3

    try:
        for round_num in range(1, MAX_SEARCH_ROUNDS + 1):
            if round_num == 1:
                context_prompt = f"学习主题: {topic}\n\n目标: {learning_goal}\n\n请规划首次搜索策略，输出 JSON:"
            else:
                prev_summary = f"已完成 {round_num - 1} 轮搜索，共 {len(all_search_results)} 条结果"
                context_prompt = f"""学习主题: {topic}
目标: {learning_goal}

{prev_summary}
{_summarize_existing_results(all_search_results, max_items=15)}

请审视现有资料是否充分。如果还有信息缺口，规划补充搜索；如果充足，输出 decision=sufficient。输出 JSON:"""

            plan_messages = [
                {"role": "system", "content": SEARCH_PLANNING_PROMPT},
                {"role": "user", "content": context_prompt}
            ]
            plan_result = llm.chat_json(plan_messages, max_tokens=4096)
            decision = plan_result.get("decision", "search")

            if decision == "sufficient":
                break

            searches = plan_result.get("searches", [])
            if not searches:
                break

            if searches and isinstance(searches[0], dict):
                queries = [s.get("query", "") for s in searches if s.get("query")]
            else:
                queries = [q for q in searches if isinstance(q, str) and q]

            if not queries:
                break

            round_results, round_images = execute_searches(queries)

            existing_urls = {r.get("url", "") for r in all_search_results}
            new_items = [item for item in round_results if item.get("url", "") not in existing_urls]
            all_search_results.extend(new_items)

            existing_img_urls = {img.get("url", "") for img in all_images}
            new_imgs = [img for img in round_images if img.get("url", "") not in existing_img_urls]
            all_images.extend(new_imgs)

        search_result_count = len(all_search_results)
        if all_search_results:
            search_context = _format_search_results(all_search_results)
        logger.info(f"  [资源生成] 模块{module_order} 搜索完成: {search_result_count} 条结果")

    except Exception as e:
        logger.warning(f"  [资源生成] 模块{module_order} 搜索异常: {str(e)[:120]}，降级为无搜索生成")

    # ==================== 内容生成 ====================
    if search_context:
        image_context = _format_image_results(all_images, max_images=6)
        image_section = ""
        if image_context:
            image_section = f"""

## 可用图片（从中选择最多 3 张最相关的，用 ![描述](URL) 嵌入正文中对应段落旁）
{image_context}"""

        gen_user_prompt = f"""请基于以下搜索结果生成学习内容（必须以搜索结果为主要依据，用自己的知识补充细节）。

主题: {topic}
学习目标: {learning_goal}
{style_text}

## 搜索结果（共 {len(all_search_results)} 条，请按编号 [1] [2] ... 在正文中引用）
{search_context}{image_section}

## 生成要求
1. 正文中必须用 [编号] 标注信息来源，例如："深度学习是机器学习的分支 [1]，其核心是神经网络 [2][3]"
2. references 字段列出你实际引用的搜索结果编号和标题
3. 如果搜索结果覆盖不足，可以用自己的知识补充，但需标注 "[综合知识]"
4. 输出 JSON:"""
    else:
        gen_user_prompt = f"""请生成以下主题的学习内容:

主题: {topic}
学习目标: {learning_goal}
{style_text}

请基于你的知识生成详细的学习内容，输出 JSON:"""

    gen_messages = [
        {"role": "system", "content": RESOURCE_GENERATOR_PROMPT},
        {"role": "user", "content": gen_user_prompt}
    ]

    try:
        def _on_chunk(chunk: str):
            if sse_callback:
                try:
                    sse_callback(f'data: {json.dumps({"type": "resource_stream_text", "resource_id": resource_id, "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        result = llm.chat_json_stream(gen_messages, on_chunk=_on_chunk, max_tokens=6144, stream_field="content")

        # 图片处理
        content_text = result.get("content", "")
        if all_images and "![" not in content_text:
            result["images"] = all_images[:3]

        result["module_order"] = module_order
        result["module_id"] = module_info.get("module_id", module_order)

        logger.info(f"  [资源生成] 模块{module_order} 生成完成: {result.get('title', '')}")
        record_from_mimo(llm, 0, "resource_generation", None)

        return result

    except Exception as e:
        logger.error(f"  [资源生成] 模块{module_order} 生成失败: {str(e)}")
        return {
            "module_order": module_order,
            "module_id": module_info.get("module_id", module_order),
            "title": module_title,
            "content": f"内容生成失败: {str(e)}",
            "description": module_desc,
            "error": str(e),
        }


# ==================== 节点函数 ====================

def resource_generator_node(state: AgentState) -> Dict[str, Any]:
    """多模态资源自主生成智能体节点 - 并行生成所有模块"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown", {})
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])
    sse_callback = state.get("sse_callback")
    placeholder_map = state.get("placeholder_resource_map", {})

    logger.info(f"{'='*60}")
    logger.info(f"  [资源生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    # 确定需要生成的模块列表
    modules = task_breakdown.get("modules", [])
    target_modules = []

    if modules:
        # 筛选未被 RAG 覆盖的模块
        covered_titles = set()
        for chunk in rag_chunks:
            for h in chunk.get("heading", []):
                covered_titles.add(h.lower())

        for m in modules:
            title = m.get("title", "")
            if not any(title.lower() in ct for ct in covered_titles):
                target_modules.append(m)

        if not target_modules:
            # 所有模块都已覆盖，全部重新生成
            target_modules = modules
            logger.info(f"  [资源生成智能体] 所有模块已覆盖，全部重新生成")
        else:
            logger.info(f"  [资源生成智能体] 发现 {len(target_modules)} 个未覆盖模块")
    else:
        # 无模块信息，创建单模块
        target_modules = [{"title": learning_goal, "description": ""}]
        logger.info(f"  [资源生成智能体] 无模块信息，单模块生成")

    logger.info(f"  [资源生成智能体] 共 {len(target_modules)} 个模块需要生成")

    # 单模块场景：通过回调创建占位记录
    if not placeholder_map and target_modules:
        create_placeholder_cb = state.get("create_placeholder_callback")
        if create_placeholder_cb:
            try:
                placeholder_map = create_placeholder_cb(target_modules)
            except Exception as e:
                logger.warning(f"  [资源生成智能体] 创建占位资源失败: {e}")

    # 通知前端创建侧栏占位条目
    if placeholder_map:
        _emit(state, "resource_stream_start", json.dumps(list(placeholder_map.values()), ensure_ascii=False))

    # ==================== 并行生成所有模块 ====================
    if len(target_modules) == 1:
        # 单模块：直接生成（不启动线程池）
        module = target_modules[0]
        placeholder = placeholder_map.get(1, {})
        res_id = placeholder.get("id", 0)
        result = _generate_single_module(
            module, 1, learning_goal, user_profile,
            sse_callback, res_id,
        )
        module_list = [result]
    else:
        # 多模块：并行生成
        logger.info(f"  [资源生成智能体] 使用并行模式，共 {len(target_modules)} 个模块")

        async def run_parallel():
            loop = asyncio.get_event_loop()
            tasks = []
            for i, module in enumerate(target_modules):
                module_order = i + 1
                placeholder = placeholder_map.get(module_order, {})
                res_id = placeholder.get("id", 0)
                task = loop.run_in_executor(
                    None,
                    _generate_single_module,
                    module,
                    module_order,
                    learning_goal,
                    user_profile,
                    sse_callback,
                    res_id,
                )
                tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            raw_results = loop.run_until_complete(run_parallel())
            loop.close()

            module_list = []
            for i, res in enumerate(raw_results):
                if isinstance(res, Exception):
                    logger.error(f"  [资源生成智能体] 模块{i+1} 异常: {str(res)}")
                    module_list.append({
                        "module_order": i + 1,
                        "module_id": i + 1,
                        "title": target_modules[i].get("title", f"模块 {i+1}"),
                        "content": f"生成失败: {str(res)}",
                        "error": str(res),
                    })
                else:
                    module_list.append(res)

            logger.info(f"  [资源生成智能体] 并行生成完成: {len(module_list)} 个模块")
        except Exception as e:
            logger.error(f"  [资源生成智能体] 并行执行异常: {str(e)}")
            return {
                "error": f"并行生成失败: {str(e)}",
                "current_step": f"资源生成智能体: 并行执行异常",
            }

    # ==================== 构建返回结果 ====================
    # 按 module_order 排序
    module_list.sort(key=lambda x: x.get("module_order", 0))

    # 构建 orchestrated_content（兼容审查流程）
    orchestrated_content = {
        "title": task_breakdown.get("title", learning_goal),
        "modules": module_list,
    }

    logger.info(f"  [资源生成智能体] 全部完成: {len(module_list)} 个模块")

    # 自主异常检测：检查生成内容是否与学习目标根本偏离
    # 尤其当所有模块都生成失败或有错误时，高度可疑
    error_count = sum(1 for m in module_list if m.get("error"))
    content_previews = []
    for m in module_list[:3]:
        content = m.get("content", "")
        if isinstance(content, str):
            content_previews.append(f"{m.get('title', '')}: {content[:150]}")
    anomaly_summary = f"目标: {learning_goal[:200]}; 生成模块: {'; '.join(content_previews)}"
    if error_count == len(module_list) and len(module_list) > 0:
        anomaly_summary += " (警告: 所有模块生成均失败)"

    from app.agents.anomaly_checker import check_content_alignment
    is_aligned, anomaly_reason = check_content_alignment(learning_goal, anomaly_summary)
    if not is_aligned:
        logger.warning(f"  [资源生成智能体] 自主检测到内容偏离: {anomaly_reason}")
        return {
            "agent_anomaly": True,
            "anomaly_reason": anomaly_reason,
            "module_list": module_list,
            "current_step": f"资源生成智能体: 检测到生成内容偏离 - {anomaly_reason}",
            "stream_events": [{
                "event_type": "thinking",
                "agent": "resource_generator",
                "data": {"message": f"检测到生成内容与目标偏离: {anomaly_reason}"},
                "step_description": f"异常中断: {anomaly_reason}"
            }],
        }

    logger.info(f"{'='*60}")

    return {
        "generated_content": module_list[0] if len(module_list) == 1 else None,
        "orchestrated_content": orchestrated_content if len(module_list) > 1 else None,
        "module_list": module_list,
        "current_step": f"资源生成智能体: 已自主生成 {len(module_list)} 个模块",
        "stream_events": [{
            "event_type": "content",
            "agent": "resource_generator",
            "data": orchestrated_content,
            "step_description": f"自主生成 {len(module_list)} 个模块",
        }],
    }
