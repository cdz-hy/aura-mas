"""
智能辅导智能体 - 针对用户当前点击的模块内容进行个性化辅导
独立端点调用，不加入主 LangGraph 图
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.agents.llm_factory import get_tutor_llm
from app.agents.enhanced_search import search_web
from app.services.db.java_client import java_client
from app.services.retrieval import HybridRetrievalService
from app.agents.conversation_compressor import build_chat_history_with_context
from app.utils.profile_utils import ensure_learning_behavior_fields, update_learning_behavior
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("agents.tutor_agent")

RETRIEVAL_SERVICE: HybridRetrievalService = None


def _get_retrieval_service() -> HybridRetrievalService:
    global RETRIEVAL_SERVICE
    if RETRIEVAL_SERVICE is None:
        RETRIEVAL_SERVICE = HybridRetrievalService()
    return RETRIEVAL_SERVICE


ANALYSIS_PROMPT = """你是一个智能辅导助手。用户正在学习某个模块，针对该模块提出了问题。

## 你的任务
1. 判断用户的问题是否与当前模块内容相关
2. 如果相关，提取 2-3 个搜索关键点，用于检索更详细的解答资料
3. 如果不相关，礼貌地引导用户回到当前模块主题

## 重要：相关性判断规则
- 如果当前模块是测验(quiz)，用户问关于题目、答案、解析、得分、错题、答题情况等问题，都视为**相关**
- 用户问"这道题怎么做"、"为什么错了"、"帮我讲解一下"等，只要在测验上下文中，都视为**相关**
- 用户问"你好"、"谢谢"等寒暄，视为**不相关**
- 只有完全与模块内容无关的问题（如聊天气、问其他话题）才视为不相关

## 搜索关键点规则（极其重要）
- 每个关键点必须是**自包含的完整查询**，单独拿出来就能准确表达用户意图
- **严禁拆分**：不要把「南昌航空大学软件学院」拆成「南昌航空大学」和「软件学院」，应保持为「南昌航空大学软件学院」
- 保留所有修饰语和限定词，确保上下文不丢失
- 每个关键点应是一个有意义的、独立的搜索查询短语

## 输出格式
严格输出 JSON：
{
  "related": true/false,
  "search_points": ["完整查询1", "完整查询2"],
  "analysis": "简要分析用户问题与模块内容的关系"
}"""


NO_RESOURCE_ANALYSIS_PROMPT = """你是一个智能辅导助手。用户没有选择具体的学习模块，直接向你提问。

## 你的任务
1. 判断用户的问题是否明确，能否判断出用户想要学习或了解什么
2. 判断问题是否与当前页面相关（页面问题）
3. 如果问题明确，提取 2-3 个搜索关键点
4. 如果问题不明确，生成一句礼貌的追问

## 重要：页面上下文与页面问题
如果提供了「用户当前正在查看的页面」信息，且用户的问题是关于页面内容的（如问画像数据、学习统计、笔记内容等），则：
- 视为问题明确
- 标记 `is_page_question=true`，表示不需要搜索，页面数据已足够回答

只有真正的学习问题（如具体知识点、概念解释、技术问题等）才需要搜索关键点。

## 搜索关键点规则（极其重要）
- 每个关键点必须是**自包含的完整查询**，单独拿出来就能准确表达用户意图
- **严禁拆分**：例如：不要把「南昌航空大学软件学院」拆成「南昌航空大学」和「软件学院」，应保持为「南昌航空大学软件学院」
- 保留所有修饰语和限定词，确保上下文不丢失
- 每个关键点应是一个有意义的、独立的搜索查询短语

## 输出格式
严格输出 JSON：
{
  "clear": true/false,
  "is_page_question": true/false,
  "search_points": ["完整查询1", "完整查询2"],
  "clarification": "如果问题不明确，用自然亲切的语气追问，像朋友聊天一样引导用户说清楚想学什么；如果问题明确则为空字符串"
}"""

RESPONSE_PROMPT = """你是一个温暖亲切的辅导老师，正在一对一辅导学生。你的说话风格自然、有温度，像一个真正关心学生学习的好老师。

## 语言风格
- 像朋友一样聊天，不要太正式，可以用"你"、"咱们"这样的称呼
- 适当用一些口语化的表达，比如"其实"、"说白了"、"打个比方"、"你会发现"
- 解释概念时多用生活化的比喻和具体的例子，让抽象的东西变得好懂
- 适时给学生鼓励和肯定，比如"这个问题问得好"、"你能想到这一步已经很不错了"
- 不要每句话都以"首先"、"其次"开头，自然过渡就好

## 回答规则
1. 紧密结合当前模块内容回答问题
2. 如果有检索到的资料，优先使用资料中的信息
3. 如果提供了「用户当前正在查看的页面」数据，直接用这些数据回答，不要说"我没有你的数据"
4. 回答分点清晰，但不要太刻板，可以用"一个是...另一个是..."这种自然的表达
5. 在回答末尾自然地给 1-2 条学习建议，像是老师随口叮嘱的那样
6. 严禁使用 emoji 表情符号
7. 使用中文回复
8. 回答简洁明了，控制在 500 字以内，不要啰嗦
9. 如果提供了「可用的相关图片」，在回答中引用最相关的图片（最多2张），图片必须紧贴相关文字放置。严禁使用 Markdown 图片语法 ![描述](URL)，必须使用以下 HTML 排版模板之一：
   - 右侧悬浮图卡片（推荐，文字环绕）：<div style="float: right; max-width: 42%; margin: 8px 0 16px 16px; padding: 6px; border-radius: 12px; border: 1px solid rgba(26, 40, 71, 0.08); background: #ffffff; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: center;"><img src="图片URL" alt="说明" style="width: 100%; height: auto; border-radius: 8px; display: block;" /><div style="font-size: 10px; color: #718096; margin-top: 6px; font-weight: 500; font-family: system-ui, sans-serif; line-height: 1.3;">说明</div></div>
   - 左侧悬浮图卡片：<div style="float: left; max-width: 42%; margin: 8px 16px 16px 0; padding: 6px; border-radius: 12px; border: 1px solid rgba(26, 40, 71, 0.08); background: #ffffff; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: center;"><img src="图片URL" alt="说明" style="width: 100%; height: auto; border-radius: 8px; display: block;" /><div style="font-size: 10px; color: #718096; margin-top: 6px; font-weight: 500; font-family: system-ui, sans-serif; line-height: 1.3;">说明</div></div>
   - 居中展示大图（适合架构图、流程图）：<div style="text-align: center; margin: 28px auto; max-width: 80%; padding: 12px; border-radius: 16px; border: 1px solid rgba(26, 40, 71, 0.08); background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%); box-shadow: 0 8px 24px rgba(26, 40, 71, 0.05);"><img src="图片URL" alt="说明" style="max-width: 100%; max-height: 400px; width: auto; border-radius: 10px; display: block;" /><div style="font-size: 12px; color: #4a5568; margin-top: 10px; font-weight: 500; font-family: system-ui, sans-serif;"><span style="color: #4164b2; font-weight: bold;">◆</span>图：说明</div></div>
   - 悬浮排版后需插入 <div style="clear: both;"></div> 清除浮动
   - 只引用与回答内容密切相关的图片，如果图片与问题无关则不引用
10. 如果提供了「参考来源」，在回答末尾自然地列出主要参考来源，格式如"想深入了解可以看看：[来源标题](URL)"，最多列 3 个最相关的来源"""


TUTOR_PROFILE_PROMPT = """你是一个用户画像分析助手。根据辅导对话内容，分析用户的学习特征变化。

## 分析维度
- 学习风格维度（增量值，范围 -0.3 ~ +0.3）：
  - visual_vs_verbal: 视觉型(-1) ↔ 言语型(+1)
  - active_vs_reflective: 活跃型(-1) ↔ 沉思型(+1)
  - sensing_vs_intuitive: 感官型(-1) ↔ 直觉型(+1)
  - sequential_vs_global: 序列型(-1) ↔ 全局型(+1)
- 知识相关（列表字段，输出期望的最终状态）：
  - knowledge_base: 已掌握的知识
  - weak_areas: 薄弱点
  - interest_tags: 兴趣标签
- 其他：
  - preferred_resource_types: 偏好的资源类型
  - goal_orientation: career/exam/interest/skill

## 输出格式
严格输出 JSON：
{
  "should_update": true/false,
  "confidence": 0.0-1.0,
  "updates": {
    "visual_vs_verbal": 增量值或null,
    "active_vs_reflective": 增量值或null,
    "sensing_vs_intuitive": 增量值或null,
    "sequential_vs_global": 增量值或null,
    "learning_speed": 增量值或null,
    "engagement_level": 增量值或null,
    "preferred_difficulty": 增量值或null,
    "quiz_accuracy": 增量值或null,
    "completion_rate": 增量值或null,
    "knowledge_base": [...仅新增项...] 或 null,
    "weak_areas": [...仅新增项...] 或 null,
    "interest_tags": [...仅新增项...] 或 null,
    "preferred_resource_types": [...仅新增项...] 或 null,
    "goal_orientation": "..." 或 null
  },
  "analysis": "简要分析依据"
}

## 注意
- 所有数值字段都输出增量值（如 +0.1 或 -0.1），不要输出绝对值，系统会自动累加到当前值
- 列表字段只输出需要新增的项，系统会自动合并（只增不删）
- goal_orientation 直接输出目标值（如 "exam"），不是增量
- 如果没有足够信息判断，should_update 设为 false"""


def _format_module_content(resource: Dict[str, Any]) -> str:
    """格式化模块内容为 LLM 可读文本"""
    module_type = resource.get("moduleType", "text")
    md = resource.get("moduleData", {})
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except Exception:
            md = {}

    title = md.get("title", md.get("quiz_title", resource.get("title", "未知模块")))
    content = md.get("content", "")
    description = md.get("description", "")

    parts = [f"模块类型: {module_type}", f"标题: {title}"]
    if description:
        parts.append(f"描述: {description}")

    # quiz 类型：从 questions 数组提取题目详情 + latestResult 作答记录
    if module_type == "quiz":
        questions = md.get("questions", [])
        latest_result = md.get("latestResult", {})
        answers_map = latest_result.get("answers", {})  # {index: user_answer}
        details_map = {}
        for d in latest_result.get("details", []):
            details_map[d.get("index")] = d

        if questions:
            quiz_lines = []
            for q in questions:
                idx = q.get("index", 0)
                qtype = q.get("type", q.get("question_type", ""))
                qtext = q.get("question", q.get("question_text", ""))
                options = q.get("options", [])
                correct = q.get("correctAnswer", q.get("correct_answer", q.get("answer", "")))
                difficulty = q.get("difficulty", "")
                explanation = q.get("explanation", "")

                line = f"第{idx + 1}题 [{qtype}] 难度{difficulty}: {qtext}"
                if options:
                    line += "\n  选项: " + " | ".join(str(o) for o in options)
                if correct:
                    line += f"\n  正确答案: {correct}"

                # 用户作答记录
                detail = details_map.get(idx)
                if detail:
                    user_ans = detail.get("user_answer", "")
                    is_correct = detail.get("is_correct", False)
                    score = detail.get("score", 0)
                    feedback = detail.get("feedback", "")
                    status = "正确" if is_correct else "错误"
                    line += f"\n  用户答案: {user_ans} ({status}, 得分{score})"
                    if feedback:
                        line += f"\n  批改反馈: {feedback}"
                elif idx in answers_map:
                    line += f"\n  用户答案: {answers_map[idx]}"

                if explanation:
                    line += f"\n  解析: {explanation}"
                quiz_lines.append(line)

            # 总分概览
            total_score = latest_result.get("score", "")
            correct_count = latest_result.get("correct", "")
            total_count = latest_result.get("total", len(questions))
            summary = f"题目（共{len(questions)}道）"
            if total_score != "":
                summary += f"，总分{total_score}，答对{correct_count}/{total_count}"
            parts.append(f"{summary}:\n" + "\n".join(quiz_lines))
    elif content:
        if len(content) > 3000:
            content = content[:3000] + "...(内容已截断)"
        parts.append(f"内容:\n{content}")

    return "\n".join(parts)


def _emit(sse_callback, event_type: str, content: str):
    """推送 SSE 事件"""
    if sse_callback:
        try:
            sse_callback(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass


async def tutor_chat(
    user_id: int,
    plan_id: int,
    session_id: str,
    resource_id: int,
    user_message: str,
    sse_callback=None,
    context_type: str = "",
    context_data: str = "",
) -> str:
    """
    智能辅导核心流程。
    resource_id=0 时为无资源模式，直接围绕用户问题回答。
    context_type: 页面类型（profile/dashboard/analytics/notes 等）
    context_data: 页面数据的 JSON 字符串

    Returns:
        AI 回复文本
    """
    llm = get_tutor_llm()
    has_resource = resource_id > 0

    # 1. 获取模块内容（仅在有资源时）
    module_content = ""
    module_type = "text"
    if has_resource:
        _emit(sse_callback, "progress", "正在获取模块内容...")
        resource = {}
        try:
            resource = java_client.get_resource_by_id(resource_id)
        except Exception as e:
            logger.warning(f"  [辅导智能体] 获取资源失败: {e}")

        if resource:
            module_content = _format_module_content(resource)
            module_type = resource.get("moduleType", "text")

    # 3. 获取对话历史（带压缩上下文）
    chat_history = []
    try:
        raw_history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id, session_id=session_id, limit=200
        )
        chat_history = build_chat_history_with_context(raw_history)
    except Exception:
        pass

    # 构建历史文本
    history_text = ""
    recent = chat_history[-20:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content'][:200]}\n"

    # 4. 构建页面上下文（提前到意图分析之前，供分析阶段使用）
    import re
    page_context_section = ""
    if context_type and context_data:
        try:
            ctx = json.loads(context_data) if isinstance(context_data, str) else context_data
            if ctx:
                ctx_lines = []
                for k, v in ctx.items():
                    if v is not None and v != "" and v != []:
                        ctx_lines.append(f"- {k}: {v}")
                if ctx_lines:
                    page_context_section = f"\n\n## 用户当前正在查看的页面: {context_type}\n" + "\n".join(ctx_lines)
        except Exception:
            pass

    # 4b. 简单问题检测（问候、身份、感谢等，无需 RAG/搜索）
    _simple_pattern = re.compile(
        r'^(你好|嗨|哈喽|hi|hello|hey|你是谁|你叫什么|你能做什么|'
        r'谢谢|感谢|thanks|thank|好的|明白了|知道了|嗯|哦|'
        r'再见|拜拜|bye|早上好|下午好|晚上好|早安|晚安|'
        r'帮帮我|帮忙|在吗|在不在|有人吗)'
        r'[\s!?！？。.~]*$', re.IGNORECASE
    )
    is_simple = bool(_simple_pattern.match(user_message.strip()))

    # 5. 分析 + 提取搜索关键点
    search_points = [user_message]
    related = True
    is_page_question = False
    analysis_text = ""

    # 5a. 无资源模式：LLM 判断用户意图是否明确
    no_resource_clarification = ""
    if not has_resource and not is_simple:
        _emit(sse_callback, "progress", "正在理解你的问题...")
        no_resource_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-800:]}" if history_text else ""}
{page_context_section}

请判断用户的问题是否明确。注意：如果用户当前正在查看某个页面且问题与该页面相关（如在画像页面问"分析我的画像"），则问题应视为明确。输出 JSON:"""

        no_resource_messages = [
            {"role": "system", "content": NO_RESOURCE_ANALYSIS_PROMPT},
            {"role": "user", "content": no_resource_input},
        ]

        try:
            nr_analysis = llm.chat_json(no_resource_messages)
            record_from_mimo(llm, user_id, "tutor_no_resource_analysis")
            is_clear = nr_analysis.get("clear", True)
            is_page_question = nr_analysis.get("is_page_question", False)
            if is_clear:
                sp = nr_analysis.get("search_points", [])
                search_points = sp if sp else [user_message]
                logger.info(f"  [辅导智能体] 无资源-意图明确, 页面问题={is_page_question}, 搜索点: {search_points}")
            else:
                no_resource_clarification = nr_analysis.get("clarification", "")
                logger.info(f"  [辅导智能体] 无资源-意图不明确, 追问: {no_resource_clarification[:80]}")
        except Exception as e:
            logger.warning(f"  [辅导智能体] 无资源意图分析失败: {e}")

    if has_resource:
        _emit(sse_callback, "progress", "正在分析问题...")
        analysis_input = f"""## 当前模块内容
{module_content}


## 用户问题
{user_message}

## 对话历史
{history_text[-1000:] if history_text else "无"}

请分析用户问题与模块内容的相关性，输出 JSON:"""

        analysis_messages = [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": analysis_input},
        ]

        try:
            analysis = llm.chat_json(analysis_messages)
            record_from_mimo(llm, user_id, "tutor_analysis")
            related = analysis.get("related", True)
            search_points = analysis.get("search_points", [user_message])
            analysis_text = analysis.get("analysis", "")
        except Exception:
            pass

        logger.info(f"  [辅导智能体] 相关性: {related}, 分析: {analysis_text[:80]}")

    # 5. RAG 检索（简单问题、页面问题、意图不明确时跳过）
    rag_context = ""
    available_images: List[Dict[str, str]] = []
    logger.info(f"  [辅导智能体] RAG判断: is_simple={is_simple}, is_page_question={is_page_question}, no_resource_clarification='{no_resource_clarification}'")
    if not is_simple and not is_page_question and not no_resource_clarification:
        _emit(sse_callback, "progress", "正在检索知识库...")
        try:
            service = _get_retrieval_service()
            rag_tasks = []
            for point in search_points[:3]:
                rag_tasks.append(service.search(query=point, limit=10, rerank_top_n=5, min_rerank_score=0.5))
            rag_results = await asyncio.gather(*rag_tasks, return_exceptions=True)

            all_chunks = []
            for result in rag_results:
                if isinstance(result, dict):
                    for chunk in result.get("context_chunks", []):
                        content = chunk.get("content", "")
                        if content and len(content) > 50:
                            all_chunks.append(content[:500])
                        # 提取图片（最多 2 张）
                        if chunk.get("image_path") and len(available_images) < 2:
                            available_images.append({
                                "url": chunk["image_path"],
                                "caption": chunk.get("image_caption", ""),
                            })

            if all_chunks:
                rag_context = "\n\n".join(f"[资料{i+1}] {c}" for i, c in enumerate(all_chunks[:5]))
                logger.info(f"  [辅导智能体] RAG 检索到 {len(all_chunks)} 条资料, {len(available_images)} 张图片")
        except Exception as e:
            logger.warning(f"  [辅导智能体] RAG 检索失败: {e}")

    # 6. 网络搜索补充（RAG 不足或无结果时触发）
    web_context = ""
    search_sources: List[Dict[str, Any]] = []
    rag_insufficient = not rag_context or rag_context.count("[资料") < 2
    logger.info(f"  [辅导智能体] 网络搜索判断: is_simple={is_simple}, is_page_question={is_page_question}, rag不足={rag_insufficient}")
    if not is_simple and not is_page_question and rag_insufficient and not no_resource_clarification:
        queries = search_points[:3]
        query_text = "、".join(queries)
        _emit(sse_callback, "search_start", query_text)
        _emit(sse_callback, "progress", f"正在搜索：{query_text}")
        try:
            logger.info(f"  [辅导智能体] 网络搜索查询: {queries}")
            all_results = []
            all_web_images = []
            for q in queries:
                result = search_web(q, max_results=5)
                if result.get("error"):
                    continue
                for r in result.get("results", []):
                    all_results.append(r)
                for img in result.get("images", []):
                    all_web_images.append(img)

            # 去重
            seen_urls = set()
            unique_results = []
            for r in all_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)

            # 按 score 排序
            unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            top_results = unique_results[:10]

            if top_results:
                # 构建 LLM 用的文本上下文
                lines = []
                for i, r in enumerate(top_results):
                    title = r.get("title", "无标题")
                    snippet = r.get("snippet", "")
                    url = r.get("url", "")
                    lines.append(f"[{i+1}] {title}\n    {snippet}\n    来源: {url}")
                web_context = "\n".join(lines)

                # 收集前端展示用的来源信息
                for r in top_results:
                    source = {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": (r.get("snippet", "") or "")[:120],
                        "score": r.get("score", 0),
                    }
                    search_sources.append(source)
                    _emit(sse_callback, "search_result", json.dumps(source, ensure_ascii=False))

                logger.info(f"  [辅导智能体] 网络搜索到 {len(top_results)} 条结果")

            # RAG 没有图片时，从 web 搜索中取
            if not available_images and all_web_images:
                for img in all_web_images[:5]:
                    if img.get("url"):
                        available_images.append({
                            "url": img["url"],
                            "caption": img.get("description", ""),
                        })
                logger.info(f"  [辅导智能体] 网络搜索图片 {len(available_images)} 张")

            _emit(sse_callback, "search_done", f"共找到 {len(top_results)} 条相关资料")
        except Exception as e:
            logger.warning(f"  [辅导智能体] 网络搜索失败: {e}")
            _emit(sse_callback, "search_done", "搜索遇到问题")

    # 7. 意图不明确时，直接返回追问（跳过 LLM 生成）
    if no_resource_clarification:
        _emit(sse_callback, "progress", "")
        _emit(sse_callback, "chunk", no_resource_clarification)
        _emit(sse_callback, "done", "")
        logger.info(f"  [辅导智能体] 返回追问: {no_resource_clarification[:80]}")
        return no_resource_clarification

    # 7. LLM 生成流式回答
    _emit(sse_callback, "progress", "正在生成回答...")

    # quiz 资源始终携带 module_content，不受 related 判断影响
    quiz_always_carry = has_resource and module_type == "quiz" and module_content

    context_section = ""
    if rag_context:
        context_section = f"\n\n## 检索到的知识资料\n{rag_context}"
    if web_context:
        context_section += f"\n\n## 网络搜索结果\n{web_context}"

    # 参考来源（供 LLM 引用）
    sources_section = ""
    if search_sources:
        source_lines = []
        for i, s in enumerate(search_sources[:5], 1):
            source_lines.append(f"[来源{i}] {s['title']} - {s['url']}")
        sources_section = "\n\n## 参考来源\n" + "\n".join(source_lines)

    # 构建图片上下文（提供 URL，由 LLM 使用 HTML 模板排版）
    image_section = ""
    if available_images:
        img_lines = []
        for i, img in enumerate(available_images):
            desc = img["caption"] or "相关图片"
            img_lines.append(f"图片{i+1}URL: {img['url']}\n图片{i+1}说明: {desc}")
        image_section = "\n\n## 可用的相关图片（请使用 HTML 排版模板嵌入，严禁使用 Markdown 图片语法）\n" + "\n".join(img_lines)

    # 根据是否有资源模块构建不同的 prompt
    if is_simple:
        # 简单问候也要带上测验上下文，让 LLM 知道用户在做测验
        quiz_context_for_simple = f"\n\n## 当前测验内容\n{module_content}" if quiz_always_carry else ""
        response_input = f"""## 用户问题
{user_message}
{quiz_context_for_simple}
{page_context_section}

自然地回复用户，像朋友聊天一样。如果是问候，热情回应然后聊聊学习上的事。"""
    elif is_page_question and page_context_section:
        response_input = f"""## 用户问题
{user_message}
{page_context_section}

根据上面的页面数据回答用户。用自然亲切的语气，像老师给学生讲解一样，不要用"首先、其次"这种刻板的格式。末尾随口叮嘱一两句学习建议。"""
    elif has_resource and related:
        response_input = f"""## 当前模块内容
{module_content}


## 用户问题
{user_message}

## 问题分析
{analysis_text}
{context_section}
{sources_section}
{image_section}
{page_context_section}

请结合模块内容和检索资料，用自然亲切的语气像老师给学生讲解一样回答。末尾随口叮嘱一两句学习建议。"""
    elif quiz_always_carry:
        # quiz 资源即使 related=False 也带上题目和作答记录
        response_input = f"""## 当前测验内容
{module_content}


## 用户问题
{user_message}

## 问题分析
{analysis_text}
{context_section}
{sources_section}
{page_context_section}

请结合测验题目和作答记录，用自然亲切的语气像老师给学生讲解一样回答。末尾随口叮嘱一两句学习建议。"""
    else:
        # 无资源模式，或问题与模块不相关
        response_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-1000:]}" if history_text else ""}
{context_section}
{sources_section}
{image_section}
{page_context_section}

请用自然亲切的语气回答用户的问题，像老师和学生聊天一样。如果有检索资料，优先使用资料中的信息。如果提供了页面上下文数据且用户的问题与页面相关，直接使用页面数据回答，不要说"我没有你的数据"。末尾随口叮嘱一两句学习建议。"""

    response_messages = [
        {"role": "system", "content": RESPONSE_PROMPT},
        {"role": "user", "content": response_input},
    ]

    ai_response = ""
    # 追踪段落边界位置，用于图片插入
    para_breaks: List[int] = []
    try:
        for chunk in llm.chat_stream(response_messages):
            ai_response += chunk
            _emit(sse_callback, "chunk", chunk)
    except Exception as e:
        logger.error(f"  [辅导智能体] 生成回答失败: {e}")
        ai_response = ai_response or "抱歉，生成回答时出现错误，请稍后再试。"
        if not ai_response:
            _emit(sse_callback, "chunk", ai_response)

    record_from_mimo(llm, user_id, "tutor_response")

    # 记录段落边界（\n\n 的位置）
    search_from = 0
    while True:
        idx = ai_response.find("\n\n", search_from)
        if idx == -1:
            break
        para_breaks.append(idx + 2)
        search_from = idx + 2

    # 如果 LLM 未引用图片，在第一个段落边界后用 HTML 排版模板插入
    if available_images and not any(img["url"] in ai_response for img in available_images):
        img_html_parts = []
        for img in available_images:
            desc = img["caption"] or "相关图片"
            url = img["url"]
            if len(available_images) >= 2 and len(img_html_parts) == 0:
                # 双图用并排模板
                img2 = available_images[1] if len(available_images) > 1 else None
                if img2:
                    desc2 = img2["caption"] or "相关图片"
                    img_html_parts.append(
                        f'<div style="margin: 28px 0; display: flex; gap: 16px; justify-content: center; align-items: stretch; width: 100%;">'
                        f'<div style="flex: 1; max-width: 48%; padding: 8px; border-radius: 12px; border: 1px solid rgba(26, 40, 71, 0.08); background: #ffffff; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: center;">'
                        f'<img src="{url}" alt="{desc}" style="width: 100%; height: auto; border-radius: 8px; display: block;" />'
                        f'<div style="font-size: 10px; color: #718096; margin-top: 8px; font-weight: 500; font-family: system-ui, sans-serif; line-height: 1.3;">{desc}</div></div>'
                        f'<div style="flex: 1; max-width: 48%; padding: 8px; border-radius: 12px; border: 1px solid rgba(26, 40, 71, 0.08); background: #ffffff; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: center;">'
                        f'<img src="{img2["url"]}" alt="{desc2}" style="width: 100%; height: auto; border-radius: 8px; display: block;" />'
                        f'<div style="font-size: 10px; color: #718096; margin-top: 8px; font-weight: 500; font-family: system-ui, sans-serif; line-height: 1.3;">{desc2}</div></div></div>'
                    )
                    break  # 两张都处理了
            else:
                # 单图用右侧悬浮模板
                img_html_parts.append(
                    f'<div style="float: right; max-width: 42%; margin: 8px 0 16px 16px; padding: 6px; border-radius: 12px; border: 1px solid rgba(26, 40, 71, 0.08); background: #ffffff; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: center;">'
                    f'<img src="{url}" alt="{desc}" style="width: 100%; height: auto; border-radius: 8px; display: block;" />'
                    f'<div style="font-size: 10px; color: #718096; margin-top: 6px; font-weight: 500; font-family: system-ui, sans-serif; line-height: 1.3;">{desc}</div></div>'
                    f'<div style="clear: both;"></div>'
                )

        img_block = "\n".join(img_html_parts)

        if para_breaks:
            insert_pos = para_breaks[0]
            corrected = ai_response[:insert_pos] + img_block + ai_response[insert_pos:]
        else:
            corrected = ai_response + img_block

        _emit(sse_callback, "replace", corrected)
        ai_response = corrected
        logger.info(f"  [辅导智能体] 图片已用 HTML 模板插入到第 1 个段落后")

    _emit(sse_callback, "done", "")
    logger.info(f"  [辅导智能体] 回答完成，长度: {len(ai_response)} 字符")

    # 8. 异步更新用户画像（合并式更新，不覆盖）
    try:
        user_profile = java_client.get_user_profile(user_id)
        current_behavior = ensure_learning_behavior_fields(user_profile.get("learning_behavior", {}))

        profile_input = f"""## 当前用户画像
- 知识基础: {current_behavior.get('knowledge_base', [])}
- 薄弱点: {current_behavior.get('weak_areas', [])}
- 兴趣标签: {current_behavior.get('interest_tags', [])}
- 视觉-言语: {current_behavior.get('visual_vs_verbal', 0.0)}
- 活跃-沉思: {current_behavior.get('active_vs_reflective', 0.0)}
- 感官-直觉: {current_behavior.get('sensing_vs_intuitive', 0.0)}
- 序列-全局: {current_behavior.get('sequential_vs_global', 0.0)}
- 偏好资源类型: {current_behavior.get('preferred_resource_types', [])}
- 目标导向: {current_behavior.get('goal_orientation', 'exam')}

## 辅导对话
用户: {user_message}
助手: {ai_response[:500]}

请分析是否有需要更新的画像信息，输出 JSON:"""

        profile_messages = [
            {"role": "system", "content": TUTOR_PROFILE_PROMPT},
            {"role": "user", "content": profile_input},
        ]

        profile_result = llm.chat_json(profile_messages)
        record_from_mimo(llm, user_id, "tutor_profile_analysis")
        should_update = profile_result.get("should_update", False)
        updates = profile_result.get("updates", {})
        confidence = profile_result.get("confidence", 0.5)

        if should_update and updates:
            # 使用与 LangGraph 相同的合并逻辑
            updated_behavior = update_learning_behavior(
                current=current_behavior,
                updates=updates,
                confidence=confidence,
            )
            reason = profile_result.get("analysis", "辅导对话自动更新")
            java_client.save_user_profile(user_id, updated_behavior, reason)
            logger.info(f"  [辅导智能体] 画像更新成功 (置信度: {confidence:.2f})")
        else:
            logger.info(f"  [辅导智能体] 无需更新画像")
    except Exception as e:
        logger.warning(f"  [辅导智能体] 画像更新失败: {e}")

    return ai_response
