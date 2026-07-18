"""
智能辅导智能体 - 支持 ReAct 工具调用模式
独立端点调用，不加入主 LangGraph 图
"""
import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from app.agents.llm_factory import get_tutor_llm
from app.agents.enhanced_search import search_web
from app.services.db.java_client import java_client
from app.services.retrieval import HybridRetrievalService
from app.agents.conversation_compressor import build_chat_history_with_context
from app.utils.profile_utils import ensure_learning_behavior_fields, update_learning_behavior
from app.utils.token_recorder import record_from_mimo
from app.prompts.tutor import TUTOR_REACT_PROMPT, RESPONSE_PROMPT, TUTOR_PROFILE_PROMPT

logger = logging.getLogger("agents.tutor_agent")

RETRIEVAL_SERVICE: HybridRetrievalService = None

# ReAct 最大轮数
MAX_REACT_ROUNDS = 5

# 工具中文名映射（用于 SSE 推送）
TOOL_NAME_MAP = {
    "get_resource_content": "获取模块内容",
    "get_plan_modules": "获取计划模块列表",
    "get_user_profile": "获取用户画像",
    "get_study_stats": "获取学习统计",
    "get_quiz_stats": "获取答题统计",
    "get_quiz_records": "获取答题记录",
    "search_knowledge": "搜索知识库",
    "search_web": "网络搜索",
}


def _get_retrieval_service() -> HybridRetrievalService:
    global RETRIEVAL_SERVICE
    if RETRIEVAL_SERVICE is None:
        RETRIEVAL_SERVICE = HybridRetrievalService()
    return RETRIEVAL_SERVICE


def _emit(sse_callback, event_type: str, content: str):
    """推送 SSE 事件"""
    if sse_callback:
        try:
            sse_callback(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass


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


def _format_modules_list(modules: List[Dict[str, Any]]) -> str:
    """格式化模块列表"""
    if not modules:
        return "暂无模块数据"
    lines = []
    for i, m in enumerate(modules[:20], 1):
        mid = m.get("id", m.get("resourceId", ""))
        title = m.get("title", m.get("moduleTitle", "未知"))
        mtype = m.get("moduleType", m.get("type", "text"))
        status = m.get("status", "")
        lines.append(f"{i}. [{mtype}] {title} (ID: {mid}, 状态: {status})")
    return "\n".join(lines)


def _format_profile(profile: Dict[str, Any], fields: List[str] = None) -> str:
    """格式化用户画像"""
    if not profile:
        return "暂无用户画像数据"

    lb = profile.get("learning_behavior", {})
    if not lb:
        return "暂无学习行为数据"

    # 如果指定了字段，只返回这些字段
    if fields:
        selected = {}
        for f in fields:
            if f in lb:
                selected[f] = lb[f]
        if selected:
            lines = [f"- {k}: {v}" for k, v in selected.items()]
            return "\n".join(lines)
        return "未找到指定字段"

    # 返回常用字段
    lines = []
    if lb.get("knowledge_base"):
        lines.append(f"- 已掌握知识: {lb['knowledge_base']}")
    if lb.get("weak_areas"):
        lines.append(f"- 薄弱点: {lb['weak_areas']}")
    if lb.get("interest_tags"):
        lines.append(f"- 兴趣标签: {lb['interest_tags']}")
    if lb.get("preferred_resource_types"):
        lines.append(f"- 偏好资源类型: {lb['preferred_resource_types']}")
    if lb.get("goal_orientation"):
        lines.append(f"- 目标导向: {lb['goal_orientation']}")

    # 学习风格维度
    style_dims = []
    for dim in ["visual_vs_verbal", "active_vs_reflective", "sensing_vs_intuitive", "sequential_vs_global"]:
        val = lb.get(dim)
        if val is not None:
            style_dims.append(f"{dim}: {val}")
    if style_dims:
        lines.append(f"- 学习风格: {', '.join(style_dims)}")

    return "\n".join(lines) if lines else "暂无详细画像数据"


def _format_quiz_stats(stats: Dict[str, Any]) -> str:
    """格式化答题统计"""
    if not stats:
        return "暂无答题统计数据"

    lines = []
    if "accuracy" in stats:
        lines.append(f"- 总正确率: {stats['accuracy']}%")
    if "totalQuestions" in stats:
        lines.append(f"- 总题数: {stats['totalQuestions']}")
    if "correctCount" in stats:
        lines.append(f"- 答对数: {stats['correctCount']}")
    if "recentAccuracy" in stats:
        lines.append(f"- 近期正确率: {stats['recentAccuracy']}%")
    if "streakDays" in stats:
        lines.append(f"- 连续学习天数: {stats['streakDays']}")

    return "\n".join(lines) if lines else "暂无统计数据"


def _format_quiz_records(records: List[Dict[str, Any]]) -> str:
    """格式化答题记录"""
    if not records:
        return "暂无答题记录"

    lines = []
    for i, r in enumerate(records[:10], 1):
        question = r.get("question", r.get("questionText", ""))[:50]
        user_answer = r.get("userAnswer", r.get("answer", ""))
        is_correct = r.get("correct", r.get("isCorrect", None))
        score = r.get("score", "")
        status = "正确" if is_correct else ("错误" if is_correct is not None else "未知")
        lines.append(f"{i}. {question}... → 答案: {user_answer} ({status}, 得分: {score})")

    return "\n".join(lines)


def _format_dashboard_stats(stats: Dict[str, Any]) -> str:
    """格式化仪表盘统计数据（包含学习时长）"""
    if not stats:
        return "暂无统计数据"

    lines = []

    # 学习时长
    if "todayStudyMinutes" in stats:
        minutes = stats["todayStudyMinutes"]
        if minutes >= 60:
            hours = minutes // 60
            mins = minutes % 60
            lines.append(f"- 今日学习时长: {hours}小时{mins}分钟")
        else:
            lines.append(f"- 今日学习时长: {minutes}分钟")

    if "totalStudyMinutes" in stats:
        minutes = stats["totalStudyMinutes"]
        if minutes >= 60:
            hours = minutes // 60
            mins = minutes % 60
            lines.append(f"- 总学习时长: {hours}小时{mins}分钟")
        else:
            lines.append(f"- 总学习时长: {minutes}分钟")

    # 学习进度
    if "completedModules" in stats and "totalModules" in stats:
        lines.append(f"- 已完成模块: {stats['completedModules']}/{stats['totalModules']}")

    if "completionRate" in stats:
        lines.append(f"- 完成率: {stats['completionRate']}%")

    # 答题统计
    if "quizAccuracy" in stats:
        lines.append(f"- 答题正确率: {stats['quizAccuracy']}%")

    if "totalQuizzes" in stats:
        lines.append(f"- 总答题数: {stats['totalQuizzes']}")

    # 连续学习
    if "streakDays" in stats:
        lines.append(f"- 连续学习天数: {stats['streakDays']}天")

    # 今日学习
    if "todayQuizzes" in stats:
        lines.append(f"- 今日答题数: {stats['todayQuizzes']}")

    if "todayCompletedModules" in stats:
        lines.append(f"- 今日完成模块: {stats['todayCompletedModules']}")

    return "\n".join(lines) if lines else "暂无统计数据"


async def _search_knowledge(query: str) -> str:
    """搜索知识库（RAG）"""
    try:
        service = _get_retrieval_service()
        result = await service.search(query=query, limit=10, rerank_top_n=5, min_rerank_score=0.5)

        chunks = result.get("context_chunks", [])
        if not chunks:
            return "未找到相关知识库资料"

        lines = []
        for i, chunk in enumerate(chunks[:5], 1):
            content = chunk.get("content", "")[:300]
            source = chunk.get("source", "")
            lines.append(f"[{i}] {content}")
            if source:
                lines.append(f"    来源: {source}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"  [辅导智能体] RAG 检索失败: {e}")
        return f"知识库检索失败: {str(e)}"


def _search_web_sync(query: str) -> Dict[str, Any]:
    """网络搜索（同步版本），返回结果和图片"""
    try:
        result = search_web(query, max_results=5)

        if result.get("error"):
            return {"text": f"网络搜索失败: {result['error']}", "images": []}

        results = result.get("results", [])
        images = result.get("images", [])

        if not results:
            return {"text": "未找到相关网络资料", "images": []}

        lines = []
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "无标题")
            snippet = r.get("snippet", "")[:200]
            url = r.get("url", "")
            lines.append(f"[{i}] {title}\n    {snippet}\n    来源: {url}")

        # 处理图片
        web_images = []
        for img in images[:5]:
            if img.get("url"):
                web_images.append({
                    "url": img["url"],
                    "caption": img.get("description", ""),
                })

        return {"text": "\n".join(lines), "images": web_images}
    except Exception as e:
        logger.warning(f"  [辅导智能体] 网络搜索失败: {e}")
        return {"text": f"网络搜索失败: {str(e)}", "images": []}


async def _execute_tool(action: Dict[str, Any], user_id: int, plan_id: int, resource_id: int) -> Dict[str, Any]:
    """执行工具调用，返回结果文本和图片"""
    act_name = action.get("action", "")

    try:
        if act_name == "get_resource_content":
            rid = action.get("resource_id", resource_id)
            if not rid:
                return {"text": "未指定资源 ID", "images": []}
            resource = java_client.get_resource_by_id(int(rid))
            if resource:
                return {"text": _format_module_content(resource), "images": []}
            return {"text": "未找到该资源", "images": []}

        elif act_name == "get_plan_modules":
            modules = java_client.get_plan_resources(plan_id)
            return {"text": _format_modules_list(modules), "images": []}

        elif act_name == "get_user_profile":
            profile = java_client.get_user_profile(user_id)
            fields = action.get("fields", [])
            return {"text": _format_profile(profile, fields if fields else None), "images": []}

        elif act_name == "get_quiz_stats":
            stats = java_client.get_user_quiz_stats(user_id, plan_id)
            return {"text": _format_quiz_stats(stats), "images": []}

        elif act_name == "get_study_stats":
            stats = java_client.get_dashboard_stats(user_id)
            return {"text": _format_dashboard_stats(stats), "images": []}

        elif act_name == "get_quiz_records":
            rid = action.get("resource_id", resource_id)
            if not rid:
                return {"text": "未指定资源 ID", "images": []}
            records = java_client.get_quiz_records_by_resource(user_id, int(rid))
            return {"text": _format_quiz_records(records), "images": []}

        elif act_name == "search_knowledge":
            query = action.get("query", "")
            if not query:
                return {"text": "未指定搜索关键词", "images": []}
            text = await _search_knowledge(query)
            return {"text": text, "images": []}

        elif act_name == "search_web":
            query = action.get("query", "")
            if not query:
                return {"text": "未指定搜索关键词", "images": []}
            return _search_web_sync(query)

        else:
            return {"text": f"未知工具: {act_name}", "images": []}

    except Exception as e:
        logger.error(f"  [辅导智能体] 工具 {act_name} 执行失败: {e}")
        return {"text": f"工具执行失败: {str(e)}", "images": []}


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
    智能辅导核心流程（ReAct 模式）。
    resource_id=0 时为无资源模式，直接围绕用户问题回答。
    context_type: 页面类型（profile/dashboard/analytics/notes 等）
    context_data: 页面数据的 JSON 字符串

    Returns:
        AI 回复文本
    """
    llm = get_tutor_llm()
    has_resource = resource_id > 0

    # 1. 简单问题检测（问候、身份、感谢等，无需工具调用）
    _simple_pattern = re.compile(
        r'^(你好|嗨|哈喽|hi|hello|hey|你是谁|你叫什么|你能做什么|'
        r'谢谢|感谢|thanks|thank|好的|明白了|知道了|嗯|哦|'
        r'再见|拜拜|bye|早上好|下午好|晚上好|早安|晚安|'
        r'帮帮我|帮忙|在吗|在不在|有人吗)'
        r'[\s!?！？。.~]*$', re.IGNORECASE
    )
    is_simple = bool(_simple_pattern.match(user_message.strip()))

    if is_simple:
        _emit(sse_callback, "progress", "")
        # 简单问候直接用 LLM 生成回答
        simple_messages = [
            {"role": "system", "content": "你是一个温暖亲切的辅导老师。像朋友一样自然地回复用户，热情回应然后聊聊学习上的事。严禁使用 emoji。使用中文回复。"},
            {"role": "user", "content": user_message},
        ]
        ai_response = ""
        try:
            for chunk in llm.chat_stream(simple_messages):
                ai_response += chunk
                _emit(sse_callback, "chunk", chunk)
        except Exception as e:
            logger.error(f"  [辅导智能体] 简单问题回答失败: {e}")
            ai_response = "你好！有什么学习上的问题可以问我哦。"
            _emit(sse_callback, "chunk", ai_response)

        _emit(sse_callback, "done", "")
        return ai_response

    # 2. 获取对话历史
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

    # 3. 构建页面上下文
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

    # 4. ReAct 循环
    _emit(sse_callback, "progress", "正在理解你的问题...")

    react_history = []
    tool_results_context = []  # 收集工具调用结果，用于最终回答
    available_images: List[Dict[str, str]] = []  # 收集图片

    # 构造当前资源信息（告知 LLM 用户正在查看哪个模块）
    current_resource_section = ""
    if has_resource:
        current_resource_section = f"""
## 用户当前正在查看的学习模块
- 资源 ID: {resource_id}
- 如果用户问关于"这个测验"、"这道题"、"当前模块"等，指的是这个资源
- 请使用 get_resource_content 工具获取该模块的详细内容"""

    for round_num in range(1, MAX_REACT_ROUNDS + 1):
        # 构造工具调用历史文本
        react_context = ""
        if react_history:
            react_context = "\n\n## 工具调用记录\n" + "\n".join(react_history)

        # 构造用户输入
        user_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-800:]}" if history_text else ""}
{current_resource_section}
{page_context_section}
{react_context}

请分析学生的问题，决定是否需要调用工具获取信息，输出 JSON:"""

        messages = [
            {"role": "system", "content": TUTOR_REACT_PROMPT.format(max_rounds=MAX_REACT_ROUNDS)},
            {"role": "user", "content": user_input},
        ]

        # 推送思考开始事件
        _emit(sse_callback, "thinking_start", f"第 {round_num} 轮思考")

        # 调用 LLM，流式推送 thought
        def _on_thought_chunk(chunk_text):
            _emit(sse_callback, "thinking_chunk", chunk_text)

        try:
            react_result = llm.chat_json_stream(messages, on_chunk=_on_thought_chunk, stream_field="thought")
            record_from_mimo(llm, user_id, "tutor_react")
        except Exception as e:
            logger.error(f"  [辅导智能体] ReAct LLM 调用失败: {e}")
            break

        # 解析结果
        if not isinstance(react_result, dict):
            logger.warning(f"  [辅导智能体] ReAct 返回非字典: {react_result}")
            break

        thought = react_result.get("thought", "")
        decision = react_result.get("decision", "finish").lower().strip()

        logger.info(f"  [辅导智能体] ReAct 轮次 {round_num}: decision={decision}, thought={thought[:80]}...")

        if decision == "tool_call":
            # 执行工具调用
            actions = react_result.get("actions", [])
            if not actions:
                logger.warning("  [辅导智能体] tool_call 但 actions 为空")
                break

            for act in actions:
                act_name = act.get("action", "")
                tool_display = TOOL_NAME_MAP.get(act_name, act_name)

                _emit(sse_callback, "progress", f"正在{tool_display}...")
                logger.info(f"  [辅导智能体] 执行工具: {act_name}")

                result = await _execute_tool(act, user_id, plan_id, resource_id)

                # 提取文本和图片
                result_text = result.get("text", "")
                result_images = result.get("images", [])

                # 收集图片（最多 2 张）
                for img in result_images:
                    if img.get("url") and len(available_images) < 2:
                        available_images.append(img)

                # 记录工具调用结果
                react_history.append(f"工具 {act_name} 结果:\n{result_text}")
                tool_results_context.append({"tool": act_name, "result": result_text})

                logger.info(f"  [辅导智能体] 工具 {act_name} 结果长度: {len(result_text)} 字符, 图片: {len(result_images)} 张")

            # 继续下一轮
            continue

        elif decision == "finish":
            # ReAct 循环结束，生成最终回答（流式输出）
            logger.info(f"  [辅导智能体] ReAct 循环结束，开始生成流式回答")
            ai_response = await _generate_final_answer(
                llm, user_message, history_text, page_context_section,
                tool_results_context, has_resource, resource_id, user_id, sse_callback,
                available_images=available_images
            )

            # 异步更新用户画像
            await _update_user_profile(llm, user_id, user_message, ai_response)

            return ai_response

        else:
            # 未知 decision，跳出循环
            logger.warning(f"  [辅导智能体] 未知 decision: {decision}")
            break

    # 如果 ReAct 循环结束但没有返回回答（异常情况），生成兜底回答
    logger.warning("  [辅导智能体] ReAct 循环异常结束，生成兜底回答")
    ai_response = await _generate_final_answer(
        llm, user_message, history_text, page_context_section,
        tool_results_context, has_resource, resource_id, user_id, sse_callback,
        available_images=available_images
    )

    # 异步更新用户画像
    await _update_user_profile(llm, user_id, user_message, ai_response)

    return ai_response


async def _generate_final_answer(
    llm, user_message: str, history_text: str, page_context_section: str,
    tool_results: List[Dict], has_resource: bool, resource_id: int,
    user_id: int, sse_callback=None, available_images: List[Dict[str, str]] = None
) -> str:
    """生成最终回答"""
    _emit(sse_callback, "progress", "正在生成回答...")

    # 构造工具结果上下文
    tools_context = ""
    if tool_results:
        tools_context = "\n\n## 已获取的信息\n"
        for tr in tool_results:
            tools_context += f"### {TOOL_NAME_MAP.get(tr['tool'], tr['tool'])}\n{tr['result']}\n\n"

    # 构造图片上下文
    image_section = ""
    if available_images:
        img_lines = []
        for i, img in enumerate(available_images):
            desc = img.get("caption", "相关图片")
            img_lines.append(f"图片{i+1}URL: {img['url']}\n图片{i+1}说明: {desc}")
        image_section = "\n\n## 可用的相关图片（请使用 HTML 排版模板嵌入，严禁使用 Markdown 图片语法）\n" + "\n".join(img_lines)

    response_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-1000:]}" if history_text else ""}
{tools_context}
{page_context_section}
{image_section}

请根据已获取的信息，用自然亲切的语气回答学生的问题。像老师和学生聊天一样。末尾随口叮嘱一两句学习建议。"""

    response_messages = [
        {"role": "system", "content": RESPONSE_PROMPT},
        {"role": "user", "content": response_input},
    ]

    ai_response = ""
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
            desc = img.get("caption", "相关图片")
            url = img["url"]
            if len(available_images) >= 2 and len(img_html_parts) == 0:
                # 双图用并排模板
                img2 = available_images[1] if len(available_images) > 1 else None
                if img2:
                    desc2 = img2.get("caption", "相关图片")
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

    return ai_response


async def _update_user_profile(llm, user_id: int, user_message: str, ai_response: str):
    """异步更新用户画像"""
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
