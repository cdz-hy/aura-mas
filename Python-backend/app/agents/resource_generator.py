"""
多模态资源自主生成智能体 - 结合增强版 ReAct 搜索循环自主生成高质量学习内容
支持并行生成多个模块，支持自主搜索和网页提取
"""
import logging
import json
import asyncio
import concurrent.futures
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_generator_llm
from app.agents.enhanced_search import (
    SearchHistoryTracker,
    execute_actions_parallel,
    format_action_results_for_llm
)
from app.prompts.enhanced_search_prompts import (
    REACT_SEARCH_SYSTEM_PROMPT,
    CONTENT_GENERATION_WITH_SOURCES_PROMPT
)
from app.core.config import settings
from app.utils.token_recorder import record_from_mimo
from app.utils import stream_registry


def _emit(state: dict, event_type: str, content: str):
    """通过 sse_callback 实时推送 SSE 事件"""
    cb = state.get("sse_callback")
    if cb:
        try:
            cb(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass

logger = logging.getLogger("agents.resource_generator")


def _summarize_existing_results(results: List[Dict[str, str]], max_items: int = 15) -> str:
    """简要摘要已有搜索结果（保留用于向后兼容，但 ReAct 模式下不再使用）"""
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
    vv = behavior.get("visual_vs_verbal", 0.0)
    si = behavior.get("sensing_vs_intuitive", 0.0)
    sg = behavior.get("sequential_vs_global", 0.0)
    
    # 1. 详细度与文本长度偏好
    if si < -0.3:
        detail_pref = "详细度极高！必须尽可能输出极长且内容极度丰富的文本。提供极其详尽、具体的概念深度剖析、海量实例应用和事无巨细的步骤拆解，切勿精简任何细节，字数越多越好！"
    elif si > 0.3:
        detail_pref = "偏好高层概念和原理解释。核心理论讲解需尽量丰富透彻，输出较长的篇幅以确保原理解释的深度，但在举例说明时可适当保持精炼，避免过于碎片化的细节，但总体篇幅仍需保持较长且充实。"
    else:
        detail_pref = "详细度高，需要输出较长篇幅的文本。提供丰富的理论说明与充实的实例分析，请放开字数限制，尽可能详尽地展开讲解。"
        
    # 2. 图片使用偏好 (Visual vs Verbal)
    if vv <= -0.8:
        image_pref = "极度偏好视觉学习。1. 必须积极从可用图片列表中挑选多张相关的真实图片嵌入内容中。2. 请极其频繁地自主生成能够提纲挈领的 Mermaid 各种图表（flowchart、sequenceDiagram等）来直观展现知识点逻辑。注意：必须确保内容有意义需要时才生成，严禁胡编乱造事实，必须基于提供的文本或网络资源生成，且必须严格遵循 Mermaid 语法。"
    elif vv <= -0.4:
        image_pref = "强偏好视觉。1. 必须积极挑选相关的真实图片嵌入内容中。2. 对于关键且复杂的概念，请较常地自主生成一些 Mermaid 图表（如 flowchart）来辅助说明。注意：必须有必要且有意义时才生成，严禁胡编乱造，必须基于检索资源生成，严格遵循 Mermaid 语法。"
    elif vv < 0:
        image_pref = "轻微偏好视觉。自然搭配真实图片。当内容极度复杂且确有必要时，偶尔可以选择性地自主生成少量的 Mermaid 流程图（flowchart）辅助说明。严禁胡编乱造，严格遵循 Mermaid 语法。"
    elif vv > 0.3:
        image_pref = "强偏好纯文字与逻辑表述。尽量少用图片（最多插入 1 张最核心的图片）。严禁自主生成任何 Mermaid 图表。"
    else:
        image_pref = "图文平衡。自然搭配图片（1-2 张）。除非极度必要，否则不要自主生成 Mermaid 图表。"
        
    # 3. 结构偏好
    if sg < -0.3:
        struct_pref = "按严格的逻辑步骤顺序逐步讲解"
    elif sg > 0.3:
        struct_pref = "先给出全局宏观图景和最终结论，再填充细节"
    else:
        struct_pref = "结构自然，按常规逻辑推进"

    style_text = (
        "用户个性化内容偏好要求（生成时必须严格遵守）:\n"
        f"1. 详细度与篇幅：{detail_pref}\n"
        f"2. 图文配比与图片数量：{image_pref}\n"
        f"3. 结构化讲解顺序：{struct_pref}"
    )
    logger.info(f"  [资源生成] 模块{module_order} 个性化偏好约束:\n{style_text}")

    # ==================== ReAct 自主搜索循环 ====================
    MAX_REACT_ROUNDS = 6  # 最多 6 轮 ReAct 循环
    history_tracker = SearchHistoryTracker()

    try:
        system_prompt = REACT_SEARCH_SYSTEM_PROMPT.format(max_rounds=MAX_REACT_ROUNDS)

        for round_num in range(1, MAX_REACT_ROUNDS + 1):
            logger.info(f"  [ReAct] 模块{module_order} - 第 {round_num} 轮思考")

            # 构建本轮 prompt
            if round_num == 1:
                user_prompt = f"""## 研究任务
学习主题: {topic}
学习目标: {learning_goal}

这是第 1 轮，请开始规划你的搜索策略。"""
            else:
                history_summary = history_tracker.get_summary_for_llm(max_recent_snippets=15)
                user_prompt = f"""## 研究任务
学习主题: {topic}
学习目标: {learning_goal}

{history_summary}

这是第 {round_num} 轮，请基于已有信息判断是否需要继续搜索。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # LLM 思考并决策（使用 chat_json_stream 而非 chat_json，避免 response_format 兼容问题）
            react_result = llm.chat_json_stream(messages, max_tokens=4096)
            logger.debug(f"  [ReAct] LLM 原始返回: {str(react_result)[:300]}")

            # 确保 react_result 是字典
            if not isinstance(react_result, dict):
                logger.warning(f"  [ReAct] LLM 返回非字典类型: {type(react_result)}，结束搜索")
                break

            thought = str(react_result.get("thought", ""))
            decision = str(react_result.get("decision", "continue")).lower().strip()
            actions = react_result.get("actions", [])

            # 确保 actions 是列表
            if not isinstance(actions, list):
                actions = []

            logger.info(f"  [ReAct] 思考: {thought[:100]}...")
            logger.info(f"  [ReAct] 决策: {decision}, 动作数: {len(actions)}")

            # 如果决定结束
            if decision == "finish":
                logger.info(f"  [ReAct] 模块{module_order} 自主决定搜索结束")
                break

            # 如果没有动作，视为结束
            if not actions:
                logger.info(f"  [ReAct] 模块{module_order} 无动作，结束搜索")
                break

            # 验证动作格式
            valid_actions = []
            for action in actions:
                if isinstance(action, dict):
                    action_type = action.get("action", "")
                    if action_type in ["search", "extract"]:
                        valid_actions.append(action)
            if not valid_actions:
                logger.warning(f"  [ReAct] 无有效动作，结束搜索")
                break

            # 并发执行所有有效动作
            action_results = execute_actions_parallel(valid_actions)

            # 更新历史记录
            for result in action_results:
                action_type = result.get("action_type", "")

                if action_type == "search":
                    query = result.get("query", "")
                    results = result.get("results", [])
                    images = result.get("images", [])
                    if results or images:
                        history_tracker.add_search_result(query, results, images)

                elif action_type == "extract":
                    url = result.get("url", "")
                    title = result.get("title", "")
                    content = result.get("content", "")
                    success = result.get("success", False)
                    if success and content:
                        history_tracker.add_extracted_page(url, title, content)

            # 格式化结果供 LLM 观察（实际不会再次调用，但记录日志）
            observation = format_action_results_for_llm(action_results)
            logger.debug(f"  [ReAct] 观察:\n{observation[:300]}...")

        logger.info(f"  [资源生成] 模块{module_order} ReAct 搜索完成: {len(history_tracker.all_snippets)} 条片段, {len(history_tracker.extracted_pages)} 个完整网页")

    except Exception as e:
        import traceback
        logger.warning(f"  [资源生成] 模块{module_order} ReAct 搜索异常: {str(e)[:200]}，降级为无搜索生成")
        logger.debug(f"  [资源生成] 异常详情:\n{traceback.format_exc()}")

    # ==================== 内容生成 ====================
    all_content = history_tracker.get_all_content_for_generation()
    snippets = all_content["snippets"]
    extracted_pages = all_content["extracted_pages"]
    images = all_content["images"]

    # 限制传给生成阶段的资源数量（模型上下文 128K，可容纳较丰富的内容）
    MAX_SNIPPETS = 40      # 最多 35 条片段
    MAX_PAGES = 5          # 最多 5 个完整网页
    PAGE_PREVIEW = 4000    # 每个网页预览 2000 字
    SNIPPET_TEXT_LEN = 500 # 每条片段摘要 300 字
    MAX_IMAGES = 20        # 最多 20 张图片

    # 如果有搜索结果，基于搜索结果生成
    if snippets or extracted_pages:
        # 格式化搜索片段（按 score 降序，取 top N）
        sorted_snippets = sorted(snippets, key=lambda x: x.get("score", 0), reverse=True)[:MAX_SNIPPETS]
        snippet_lines = []
        for i, snippet in enumerate(sorted_snippets, 1):
            title = snippet.get("title", "无标题")
            text = (snippet.get("snippet", "") or "")[:SNIPPET_TEXT_LEN]
            url = snippet.get("url", "")
            snippet_lines.append(f"[{i}] {title}\n    {text}\n    URL: {url}")
        snippet_context = "\n\n".join(snippet_lines) if snippet_lines else "（无搜索片段）"

        # 格式化完整网页（取前 N 个）
        page_lines = []
        for i, (url, content) in enumerate(list(extracted_pages.items())[:MAX_PAGES], 1):
            page_lines.append(f"[page{i}] {url} ({len(content)} 字)")
            page_lines.append(f"{content[:PAGE_PREVIEW]}...")
        page_context = "\n\n".join(page_lines) if page_lines else "（无完整网页）"

        # 格式化图片
        image_lines = []
        for i, img in enumerate(images[:MAX_IMAGES], 1):
            desc = img.get("description", "") or "相关图片"
            url = img.get("url", "")
            image_lines.append(f"[img{i}] {desc}\n    URL: {url}")
        image_context = "\n\n".join(image_lines) if image_lines else "（无可用图片）"
        logger.info(f"  [资源生成] 模块{module_order} 传递给生成: {len(sorted_snippets)}/{len(snippets)} 条片段, {min(len(extracted_pages), MAX_PAGES)}/{len(extracted_pages)} 个网页, {min(len(images), MAX_IMAGES)}/{len(images)} 张图片")

        gen_user_prompt = f"""请基于以下搜索资源生成高质量学习内容。

## 研究主题
主题: {topic}
学习目标: {learning_goal}
{style_text}

## 搜索结果片段（共 {len(sorted_snippets)} 条，按相关度排序）
{snippet_context}

## 提取的完整网页（共 {min(len(extracted_pages), MAX_PAGES)} 个）
{page_context}

## 可用图片（共 {min(len(images), MAX_IMAGES)} 张）
{image_context}

请生成完整的学习内容，输出 JSON。"""

    else:
        # 降级：无搜索结果，基于 LLM 知识生成
        gen_user_prompt = f"""请生成以下主题的学习内容:

主题: {topic}
学习目标: {learning_goal}
{style_text}

请基于你的知识生成详细的学习内容，输出 JSON:"""

    gen_messages = [
        {"role": "system", "content": CONTENT_GENERATION_WITH_SOURCES_PROMPT},
        {"role": "user", "content": gen_user_prompt}
    ]

    try:
        def _on_chunk(chunk: str):
            if sse_callback:
                try:
                    sse_callback(f'data: {json.dumps({"type": "resource_stream_text", "resource_id": resource_id, "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        result = llm.chat_json_stream(gen_messages, on_chunk=_on_chunk, max_tokens=8192, stream_field="content")

        # 图片处理（如果生成结果没有嵌入图片，附加在结果中）
        content_text = result.get("content", "")
        if images and "![" not in content_text and "<img" not in content_text:
            result["images"] = images[:3]

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

async def resource_generator_node(state: AgentState) -> Dict[str, Any]:
    """多模态资源自主生成智能体节点 - 并行生成所有模块"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown") or {}
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])
    session_id = state.get("session_id", "")
    # 优先从 state 获取回调；回退到 stream_registry（checkpointer 序列化会丢失 callable）
    sse_callback = state.get("sse_callback") or stream_registry.get_sse_callback(session_id)
    placeholder_map = state.get("placeholder_resource_map") or stream_registry.get_placeholder_map(session_id)

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
        create_placeholder_cb = state.get("create_placeholder_callback") or stream_registry.get_create_placeholder_callback(session_id)
        if create_placeholder_cb:
            try:
                placeholder_map = create_placeholder_cb(target_modules)
                stream_registry.update_placeholder_map(session_id, placeholder_map)
            except Exception as e:
                logger.warning(f"  [资源生成智能体] 创建占位资源失败: {e}")

    # 通知前端创建侧栏占位条目
    if placeholder_map:
        logger.info(f"  [资源生成智能体] 发送 resource_stream_start，共 {len(placeholder_map)} 个占位")
        _emit(state, "resource_stream_start", json.dumps(list(placeholder_map.values()), ensure_ascii=False))
        # 若 state 中无 sse_callback，直接通过 sse_callback 推送
        if not state.get("sse_callback") and sse_callback:
            try:
                sse_callback(f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(placeholder_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    # ==================== 并行生成所有模块 ====================
    if len(target_modules) == 1:
        # 单模块：直接异步线程生成
        module = target_modules[0]
        placeholder = placeholder_map.get(1, {})
        res_id = placeholder.get("id", 0)
        result = await asyncio.to_thread(
            _generate_single_module,
            module, 1, learning_goal, user_profile,
            sse_callback, res_id,
        )
        module_list = [result]
    else:
        # 多模块：并行生成
        logger.info(f"  [资源生成智能体] 使用并行模式，共 {len(target_modules)} 个模块")

        tasks = []
        for i, module in enumerate(target_modules):
            module_order = i + 1
            placeholder = placeholder_map.get(module_order, {})
            res_id = placeholder.get("id", 0)
            task = asyncio.to_thread(
                _generate_single_module,
                module,
                module_order,
                learning_goal,
                user_profile,
                sse_callback,
                res_id,
            )
            tasks.append(task)

        try:
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

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

    if not state.get("background_generation"):
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
