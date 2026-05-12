"""
多模态资源自主生成智能体 - 结合 Tavily 网络搜索自主生成高质量学习内容
"""
import logging
import concurrent.futures
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_generator_llm
from app.core.config import settings

logger = logging.getLogger("agents.resource_generator")

SYSTEM_PROMPT = """你是一个专业的知识内容生成专家，配备网络搜索能力。当知识库中没有找到相关资料时，你需要自主决策调用搜索引擎获取最新信息，并结合搜索结果生成高质量的学习内容。

## 生成要求
1. 内容准确、专业、完整，优先使用搜索到的权威资料
2. 结构清晰，使用标题、列表、代码块等格式
3. 适当使用类比和举例帮助理解
4. 难度要匹配用户的知识基础
5. 如果涉及代码，要给出完整可运行的示例
6. 搜索结果为英文时需翻译为中文输出

## 输出格式
严格输出 JSON：
{
  "title": "内容标题",
  "content": "完整的 Markdown 格式内容",
  "key_points": ["要点1", "要点2"],
  "references": ["参考来源描述1"],
  "content_type": "text/code/mixed",
  "difficulty": "入门/初级/中级/高级"
}

## 规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 内容要充实，引用搜索结果中的具体数据或事实时要注明来源
- 代码示例要标注语言类型
- 标题必须是实际内容名称，严禁使用「第一章」「第二章」「模块一」等章节编号前缀
- 严禁生成题目/练习题/测验相关内容"""

SEARCH_PLANNING_PROMPT = """你是一个具备多轮搜索能力的智能研究助手。你的任务是规划网络搜索策略，并根据已有搜索结果判断是否需要补充搜索。

## 搜索工具
使用 Tavily 统一搜索引擎，支持中英文查询，返回网页摘要和链接。

## 首次搜索策略
- 规划 2-3 个不同角度的搜索关键词（中英文结合）
- 如果主题很简单或纯粹常识性知识，可以判定 sufficient

## 补充搜索策略（已有部分结果时）
- 审视已有结果覆盖了哪些方面，还缺少哪些方面
- 针对缺失的方面制定补充搜索
- 如果已经覆盖了足够的信息面，判定 sufficient 终止搜索

## 输出格式
严格输出 JSON，不要输出其他内容：
{
  "decision": "search" 或 "sufficient",
  "reasoning": "判断依据（1-2句话）",
  "searches": ["搜索关键词1", "搜索关键词2"]
}

注意：decision=search 时才需要 searches 数组；decision=sufficient 时 searches 留空数组即可。"""


# ==================== Tavily 搜索 ====================

def _search_tavily(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Tavily 网页搜索"""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.search(query, max_results=max_results)
        results = []
        for r in resp.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": (r.get("content") or "")[:500],
                "url": r.get("url", ""),
            })
        logger.info(f"  [Tavily] '{query}' -> {len(results)} 条结果")
        return results
    except Exception as e:
        logger.warning(f"  [Tavily] 搜索失败 '{query}': {str(e)[:120]}")
        return []


def _execute_searches(queries: List[str]) -> List[Dict[str, str]]:
    """并行执行所有搜索查询，返回去重后的结果列表"""
    all_results: List[Dict[str, str]] = []
    seen_urls: set = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_search_tavily, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                items = future.result()
                for item in items:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(item)
            except Exception as e:
                logger.warning(f"  [搜索] 任务执行异常: {str(e)[:120]}")

    return all_results


def _format_search_results(results: List[Dict[str, str]]) -> str:
    """格式化搜索结果为 LLM 可读文本"""
    lines = []
    for i, r in enumerate(results):
        title = r.get("title", "无标题")
        snippet = r.get("snippet", "")[:300]
        url = r.get("url", "")
        line = f"{i + 1}. **{title}**\n   {snippet}"
        if url:
            line += f"\n   来源: {url}"
        lines.append(line)
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
    MAX_SEARCH_ROUNDS = 5

    try:
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
{_summarize_existing_results(all_search_results, max_items=15)}

请审视现有资料是否充分覆盖了学习主题的各个方面。如果还有信息缺口，规划补充搜索；如果资料充足，输出 decision=sufficient。输出 JSON:"""

            plan_messages = [
                {"role": "system", "content": SEARCH_PLANNING_PROMPT},
                {"role": "user", "content": context_prompt}
            ]
            plan_result = llm.chat_json(plan_messages, max_tokens=1024)
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
            logger.info(f"  [资源生成智能体] 并行执行搜索...")
            round_results = _execute_searches(queries)
            logger.info(f"  [资源生成智能体] 第{round_num}轮获取 {len(round_results)} 条结果")

            # 累积结果（去重：按 URL）
            existing_urls = {r.get("url", "") for r in all_search_results}
            new_items = [item for item in round_results if item.get("url", "") not in existing_urls]
            all_search_results.extend(new_items)

            search_round_history.append(
                f"第{round_num}轮 ({decision}): {reasoning[:120]}; "
                f"搜索了 {len(queries)} 个关键词，新增 {len(round_results)} 条结果"
            )

        else:
            logger.info(f"  [资源生成智能体] 已达到最大搜索轮次 ({MAX_SEARCH_ROUNDS})，强制停止")

        search_result_count = len(all_search_results)
        logger.info(f"  [资源生成智能体] 多轮搜索完成: 共 {search_result_count} 条累积结果，{len(search_round_history)} 轮")

        if all_search_results:
            search_context = _format_search_results(all_search_results)

    except Exception as e:
        logger.warning(f"  [资源生成智能体] 搜索阶段异常: {str(e)[:200]}，降级为无搜索生成")

    # ==================== Phase 3: 内容生成 ====================
    if search_context:
        gen_user_prompt = f"""请生成以下主题的学习内容:

主题: {topic}
学习目标: {learning_goal}
{style_text}

## 网络搜索结果
{search_context}

请优先参考以上搜索结果，结合你的知识生成准确、权威的学习内容，并注明信息来源。输出 JSON:"""
    else:
        gen_user_prompt = f"""请生成以下主题的学习内容:

主题: {topic}
学习目标: {learning_goal}
{style_text}

请基于你的知识生成详细的学习内容，输出 JSON:"""

    gen_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": gen_user_prompt}
    ]

    try:
        logger.info(f"  [资源生成智能体] Phase 3: 调用 LLM 生成内容...")
        # 根据搜索结果数量动态调整 max_tokens，避免超出上下文窗口
        if search_context:
            # 有搜索结果时，输入较长，降低 max_tokens
            max_tokens = 4096
        else:
            # 无搜索结果时，输入较短，可以适当提高
            max_tokens = 6144
        result = llm.chat_json(gen_messages, max_tokens=max_tokens)

        logger.info(f"  [资源生成智能体] 生成完成!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    类型: {result.get('content_type', '未知')}")
        logger.info(f"    难度: {result.get('difficulty', '未知')}")
        logger.info(f"    要点: {', '.join(result.get('key_points', []))}")
        logger.info(f"    参考来源: {len(result.get('references', []))} 条")
        logger.info(f"    内容长度: {len(result.get('content', ''))} 字符")
        logger.info(f"{'='*60}")

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
