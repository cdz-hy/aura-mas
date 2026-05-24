"""
智能辅导智能体 - 针对用户当前点击的模块内容进行个性化辅导
独立端点调用，不加入主 LangGraph 图
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.agents.llm_factory import get_tutor_llm
from app.agents.search_utils import search_tavily, execute_searches, format_search_results
from app.services.db.java_client import java_client
from app.services.retrieval import HybridRetrievalService
from app.agents.conversation_compressor import build_chat_history_with_context

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

## 输出格式
严格输出 JSON：
{
  "related": true/false,
  "search_points": ["关键点1", "关键点2"],
  "analysis": "简要分析用户问题与模块内容的关系"
}"""


RESPONSE_PROMPT = """你是一个友好的智能辅导助手。用户正在学习某个模块，针对该模块提出了问题。

## 回答规则
1. 紧密结合当前模块内容回答问题
2. 如果有检索到的资料，优先使用资料中的信息
3. 回答要分点清晰，便于理解
4. 在回答末尾给出 1-2 条学习建议
5. 严禁使用 emoji 表情符号
6. 使用中文回复
7. 回答简洁明了，避免冗长，控制在 500 字以内"""


def _format_module_content(resource: Dict[str, Any]) -> str:
    """格式化模块内容为 LLM 可读文本"""
    module_type = resource.get("moduleType", "text")
    md = resource.get("moduleData", {})
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except Exception:
            md = {}

    title = md.get("title", resource.get("title", "未知模块"))
    content = md.get("content", "")
    description = md.get("description", "")

    parts = [f"模块类型: {module_type}", f"标题: {title}"]
    if description:
        parts.append(f"描述: {description}")
    if content:
        # 截断过长内容
        if len(content) > 3000:
            content = content[:3000] + "...(内容已截断)"
        parts.append(f"内容:\n{content}")
    return "\n".join(parts)


def _format_quiz_records(records: List[Dict]) -> str:
    """格式化用户作答记录"""
    if not records:
        return "暂无作答记录"
    lines = []
    for i, r in enumerate(records[:10], 1):
        question = r.get("questionText", r.get("question", ""))
        user_answer = r.get("userAnswer", "")
        is_correct = r.get("isCorrect", 0)
        correct_answer = r.get("correctAnswer", "")
        status = "正确" if is_correct else "错误"
        lines.append(f"第{i}题: {question[:100]}")
        lines.append(f"  用户答案: {user_answer} ({status})")
        if not is_correct:
            lines.append(f"  正确答案: {correct_answer}")
    return "\n".join(lines)


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
) -> str:
    """
    智能辅导核心流程。
    resource_id=0 时为无资源模式，直接围绕用户问题回答。

    Returns:
        AI 回复文本
    """
    llm = get_tutor_llm()
    has_resource = resource_id > 0

    # 1. 获取模块内容（仅在有资源时）
    module_content = ""
    module_type = "text"
    quiz_text = ""
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

        # 2. 如果是 quiz 类型，获取作答记录
        if module_type == "quiz":
            try:
                records = java_client.get_quiz_records_by_resource(user_id, resource_id)
                quiz_text = _format_quiz_records(records)
            except Exception as e:
                logger.warning(f"  [辅导智能体] 获取作答记录失败: {e}")

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

    # 4. 分析 + 提取搜索关键点
    search_points = [user_message]
    related = True
    analysis_text = ""

    if has_resource:
        _emit(sse_callback, "progress", "正在分析问题...")
        analysis_input = f"""## 当前模块内容
{module_content}

{f"## 用户作答记录{chr(10)}{quiz_text}" if quiz_text else ""}

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
            analysis = llm.chat_json(analysis_messages, max_tokens=512)
            related = analysis.get("related", True)
            search_points = analysis.get("search_points", [user_message])
            analysis_text = analysis.get("analysis", "")
        except Exception:
            pass

        logger.info(f"  [辅导智能体] 相关性: {related}, 分析: {analysis_text[:80]}")

    # 5. RAG 检索
    rag_context = ""
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

        if all_chunks:
            rag_context = "\n\n".join(f"[资料{i+1}] {c}" for i, c in enumerate(all_chunks[:5]))
            logger.info(f"  [辅导智能体] RAG 检索到 {len(all_chunks)} 条资料")
    except Exception as e:
        logger.warning(f"  [辅导智能体] RAG 检索失败: {e}")

    # 6. RAG 不足时，网络搜索
    web_context = ""
    if not rag_context:
        _emit(sse_callback, "progress", "知识库未找到相关内容，正在网络搜索...")
        try:
            queries = search_points[:2]
            results, _ = execute_searches(queries)
            if results:
                web_context = format_search_results(results[:5])
                logger.info(f"  [辅导智能体] 网络搜索到 {len(results)} 条结果")
        except Exception as e:
            logger.warning(f"  [辅导智能体] 网络搜索失败: {e}")

    # 7. LLM 生成流式回答
    _emit(sse_callback, "progress", "正在生成回答...")

    context_section = ""
    if rag_context:
        context_section = f"\n\n## 检索到的知识资料\n{rag_context}"
    elif web_context:
        context_section = f"\n\n## 网络搜索结果\n{web_context}"

    # 根据是否有资源模块构建不同的 prompt
    if has_resource and related:
        response_input = f"""## 当前模块内容
{module_content}

{f"## 用户作答记录{chr(10)}{quiz_text}" if quiz_text else ""}

## 用户问题
{user_message}

## 问题分析
{analysis_text}
{context_section}

请结合模块内容和检索资料，回答用户的问题，并给出学习建议。"""
    else:
        # 无资源模式，或问题与模块不相关
        response_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-1000:]}" if history_text else ""}
{context_section}

请回答用户的问题。如果有检索资料，优先使用资料中的信息。回答分点清晰，末尾给出 1-2 条学习建议。"""

    response_messages = [
        {"role": "system", "content": RESPONSE_PROMPT},
        {"role": "user", "content": response_input},
    ]

    ai_response = ""
    try:
        for chunk in llm.chat_stream(response_messages, max_tokens=2048):
            ai_response += chunk
            _emit(sse_callback, "chunk", chunk)
    except Exception as e:
        logger.error(f"  [辅导智能体] 生成回答失败: {e}")
        ai_response = "抱歉，生成回答时出现错误，请稍后再试。"
        _emit(sse_callback, "chunk", ai_response)

    _emit(sse_callback, "done", "")
    logger.info(f"  [辅导智能体] 回答完成，长度: {len(ai_response)} 字符")

    return ai_response
