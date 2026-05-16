"""
多模态资源自主生成智能体 - 结合 Tavily 网络搜索自主生成高质量学习内容
"""
import logging
import json
import concurrent.futures
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_generator_llm
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




# ==================== Tavily 搜索 ====================

def _search_tavily(query: str, max_results: int = 5) -> tuple:
    """Tavily 网页搜索，返回 (文本结果列表, 图片URL列表)"""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.search(query, max_results=max_results, include_images=True, include_image_descriptions=True)
        results = []
        for r in resp.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content") or "",
                "url": r.get("url", ""),
            })
        # 收集图片：resp 顶层有 images 列表，result 内也可能有 images
        images = []
        seen_img_urls = set()
        for img in resp.get("images", []):
            if isinstance(img, dict):
                img_url = img.get("url", "")
                img_desc = img.get("description", "")
            else:
                img_url = str(img)
                img_desc = ""
            if img_url and img_url not in seen_img_urls:
                seen_img_urls.add(img_url)
                images.append({"url": img_url, "description": img_desc})
        for r in resp.get("results", []):
            for img in r.get("images", []):
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    img_desc = img.get("description", "")
                else:
                    img_url = str(img)
                    img_desc = ""
                if img_url and img_url not in seen_img_urls:
                    seen_img_urls.add(img_url)
                    images.append({"url": img_url, "description": img_desc})
        logger.info(f"  [Tavily] '{query}' -> {len(results)} 条文本, {len(images)} 张图片")
        return results, images
    except Exception as e:
        logger.warning(f"  [Tavily] 搜索失败 '{query}': {str(e)[:120]}")
        return [], []


def _execute_searches(queries: List[str]) -> tuple:
    """并行执行所有搜索查询，返回 (去重后的文本结果列表, 去重后的图片列表)"""
    all_results: List[Dict[str, str]] = []
    all_images: List[Dict[str, str]] = []
    seen_urls: set = set()
    seen_img_urls: set = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_search_tavily, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                items, images = future.result()
                for item in items:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(item)
                for img in images:
                    img_url = img.get("url", "")
                    if img_url and img_url not in seen_img_urls:
                        seen_img_urls.add(img_url)
                        all_images.append(img)
            except Exception as e:
                logger.warning(f"  [搜索] 任务执行异常: {str(e)[:120]}")

    return all_results, all_images


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


# ==================== 节点函数 ====================

def resource_generator_node(state: AgentState) -> Dict[str, Any]:
    """多模态资源自主生成智能体节点 - 带 Tavily 网络搜索增强"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown", {})
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])
    retry_mode = state.get("retry_mode", False)
    target_module_ids = state.get("target_module_ids", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [资源生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    if retry_mode:
        logger.info(f"  重试模式: 目标模块 {target_module_ids}")

    llm = get_resource_generator_llm()

    # 确定生成主题
    modules = task_breakdown.get("modules", [])
    if retry_mode and target_module_ids and modules:
        retry_modules = [m for m in modules if (m.get("module_id") or m.get("order")) in target_module_ids]
        if not retry_modules:
            retry_modules = [m for i, m in enumerate(modules, 1) if i in target_module_ids]
        if retry_modules:
            target_desc = "、".join(m.get("title", "")[:40] for m in retry_modules)
            topic = f"{task_breakdown.get('title', learning_goal)} - 重点: {target_desc}"
            logger.info(f"  [资源生成智能体] 重试模式: 针对 {len(retry_modules)} 个未通过模块 ({target_desc})")
        else:
            topic = learning_goal
    elif modules:
        covered_titles = set()
        for chunk in rag_chunks:
            for h in chunk.get("heading", []):
                covered_titles.add(h.lower())

        uncovered = []
        for m in modules:
            title = m.get("title", "")
            if not any(title.lower() in ct for ct in covered_titles):
                uncovered.append(m)

        if uncovered:
            target_module = uncovered[0]
            topic = f"{target_module.get('title', '')}: {target_module.get('description', '')}"
            logger.info(f"  [资源生成智能体] 发现 {len(uncovered)} 个未覆盖模块，生成: {target_module.get('title', '')}")
        else:
            topic = learning_goal
            logger.info(f"  [资源生成智能体] 所有模块已覆盖，生成通用内容")
    else:
        topic = learning_goal
        logger.info(f"  [资源生成智能体] 无模块信息，直接生成")

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

    # ==================== 多轮搜索循环（最多5轮） ====================
    search_context = ""
    search_result_count = 0
    search_round_history = []
    all_search_results: List[Dict[str, str]] = []
    all_images: List[Dict[str, str]] = []
    MAX_SEARCH_ROUNDS = 5

    try:
        _emit(state, "progress", "正在规划搜索策略...")
        for round_num in range(1, MAX_SEARCH_ROUNDS + 1):
            logger.info(f"  [资源生成智能体] Phase 1 第{round_num}轮: LLM 分析搜索需求...")

            if round_num == 1:
                context_prompt = f"学习主题: {topic}\n\n目标: {learning_goal}\n\n请规划首次搜索策略，输出 JSON:"
            else:
                prev_summary = "\n".join(search_round_history)
                context_prompt = f"""学习主题: {topic}
目标: {learning_goal}

## 已完成的搜索轮次
{prev_summary}

## 当前已收集的资料摘要
{_summarize_existing_results(all_search_results, max_items=30)}

请审视现有资料是否充分覆盖了学习主题的各个方面。如果还有信息缺口，规划补充搜索；如果资料充足，输出 decision=sufficient。输出 JSON:"""

            plan_messages = [
                {"role": "system", "content": SEARCH_PLANNING_PROMPT},
                {"role": "user", "content": context_prompt}
            ]
            plan_result = llm.chat_json(plan_messages, max_tokens=4096)
            decision = plan_result.get("decision", "search")
            reasoning = plan_result.get("reasoning", "")

            logger.info(f"  [资源生成智能体] 第{round_num}轮 LLM 决策: {decision} ({reasoning[:80]})")

            if decision == "sufficient":
                logger.info(f"  [资源生成智能体] LLM 判定资料充足，停止搜索 (共 {round_num} 轮)")
                break

            searches = plan_result.get("searches", [])
            if not searches:
                logger.info(f"  [资源生成智能体] 第{round_num}轮无新搜索，停止搜索")
                break

            # 兼容 LLM 可能输出对象格式的情况
            if searches and isinstance(searches[0], dict):
                queries = [s.get("query", "") for s in searches if s.get("query")]
            else:
                queries = [q for q in searches if isinstance(q, str) and q]

            logger.info(f"  [资源生成智能体] 第{round_num}轮规划了 {len(queries)} 个搜索任务:")
            for q in queries:
                logger.info(f"    [Tavily] {q[:80]}")

            # 并行执行本轮搜索
            _emit(state, "progress", f"正在执行第 {round_num} 轮搜索（{len(queries)} 个关键词）...")
            logger.info(f"  [资源生成智能体] 并行执行搜索...")
            round_results, round_images = _execute_searches(queries)
            _emit(state, "progress", f"第 {round_num} 轮搜索完成，获取 {len(round_results)} 条结果, {len(round_images)} 张图片")
            logger.info(f"  [资源生成智能体] 第{round_num}轮获取 {len(round_results)} 条文本, {len(round_images)} 张图片")

            # 累积结果（去重：按 URL）
            existing_urls = {r.get("url", "") for r in all_search_results}
            new_items = [item for item in round_results if item.get("url", "") not in existing_urls]
            all_search_results.extend(new_items)

            # 累积图片（去重）
            existing_img_urls = {img.get("url", "") for img in all_images}
            new_imgs = [img for img in round_images if img.get("url", "") not in existing_img_urls]
            all_images.extend(new_imgs)

            search_round_history.append(
                f"第{round_num}轮 ({decision}): {reasoning[:120]}; "
                f"搜索了 {len(queries)} 个关键词，新增 {len(round_results)} 条结果"
            )

        else:
            logger.info(f"  [资源生成智能体] 已达到最大搜索轮次 ({MAX_SEARCH_ROUNDS})，强制停止")

        search_result_count = len(all_search_results)
        logger.info(f"  [资源生成智能体] 多轮搜索完成: 共 {search_result_count} 条文本, {len(all_images)} 张图片, {len(search_round_history)} 轮")

        if all_search_results:
            search_context = _format_search_results(all_search_results)

    except Exception as e:
        logger.warning(f"  [资源生成智能体] 搜索阶段异常: {str(e)[:200]}，降级为无搜索生成")

    _emit(state, "progress", f"搜索完成（共 {search_result_count} 条结果），正在生成学习内容...")

    # ==================== Phase 3: 内容生成 ====================
    if search_context:
        # 格式化图片列表供 LLM 选择嵌入
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
        logger.info(f"  [资源生成智能体] Phase 3: 调用 LLM 生成内容...")
        # 根据搜索结果数量动态调整 max_tokens，避免超出上下文窗口
        if search_context:
            max_tokens = 6144
        else:
            max_tokens = 6144
        result = llm.chat_json(gen_messages, max_tokens=max_tokens)

        _emit(state, "progress", "内容生成完成，正在整理结果...")

        # 图片处理：如果 LLM 未在正文中嵌入图片，则附加最多 3 张作为 fallback
        content_text = result.get("content", "")
        if all_images and "![" not in content_text:
            result["images"] = all_images[:3]

        logger.info(f"  [资源生成智能体] 生成完成!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    类型: {result.get('content_type', '未知')}")
        logger.info(f"    难度: {result.get('difficulty', '未知')}")
        logger.info(f"    要点: {', '.join(result.get('key_points', []))}")
        logger.info(f"    参考来源: {len(result.get('references', []))} 条")
        logger.info(f"    图片: {len(result.get('images', []))} 张")
        logger.info(f"    内容长度: {len(result.get('content', ''))} 字符")
        logger.info(f"{'='*60}")

        record_from_mimo(llm, state.get("user_id", 0), "resource_generation", state.get("task_id"))

        return {
            "generated_content": result,
            "current_step": f"资源生成智能体: 已自主生成内容 [{result.get('title', '未命名')}]",
            "stream_events": [{
                "event_type": "content",
                "agent": "resource_generator",
                "data": result,
                "step_description": f"结合 {search_result_count} 条网络搜索结果自主生成: {result.get('title', '')}"
            }],
        }

    except Exception as e:
        logger.error(f"  [资源生成智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"资源自主生成失败: {str(e)}",
            "current_step": f"资源生成智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "resource_generator",
                "data": {"error": str(e)},
                "step_description": "自主生成失败"
            }],
        }
