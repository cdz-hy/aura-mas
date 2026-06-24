"""
题目生成智能体 - 结合用户画像中的薄弱点和偏好题型，自主抉择题目类型并生成题目
可选择调用 RAG 检索相关知识点结合内容生成
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_quiz_generator_llm
from app.prompts import QUIZ_GENERATOR_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.utils import stream_registry
import json

logger = logging.getLogger("agents.quiz_generator")



def quiz_generator_node(state: AgentState) -> Dict[str, Any]:
    """题目生成智能体节点"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    rag_chunks = state.get("rag_context_chunks", [])
    user_profile = state.get("user_profile", {})
    orchestrated_content = state.get("orchestrated_content")
    chat_history = state.get("chat_history", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [题目生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    # 实时推送思考过程
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))

    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "题目生成智能体", "content": content}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_start(agent: str, prefix: str = ""):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_start", "agent": agent, "content": prefix}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_chunk(chunk: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_chunk", "content": chunk}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    _emit_thinking("正在结合薄弱点生成练习题...")

    llm = get_quiz_generator_llm()

    behavior = user_profile.get("learning_behavior", {})
    weak_points = behavior.get("weak_areas", [])
    pref_types = behavior.get("preferred_quiz_types", [])

    if weak_points:
        logger.info(f"  [题目生成智能体] 用户薄弱点: {', '.join(weak_points)}")
    if pref_types:
        logger.info(f"  [题目生成智能体] 偏好题型: {', '.join(pref_types)}")

    content_summary = ""
    if orchestrated_content:
        modules = orchestrated_content.get("modules", [])
        content_summary = "\n".join([
            f"模块{i+1} - {m.get('title', '')}: {m.get('content', '')[:200]}"
            for i, m in enumerate(modules[:5])
        ])
        logger.info(f"  [题目生成智能体] 使用编排内容: {len(modules)} 个模块")
    elif rag_chunks:
        content_summary = "\n".join([
            f"[{i+1}] {c.get('content', '')[:200]}"
            for i, c in enumerate(rag_chunks[:8])
        ])
        logger.info(f"  [题目生成智能体] 使用 RAG 检索内容: {len(rag_chunks)} 块")

    pref_text = f"偏好题型: {', '.join(pref_types)}" if pref_types else "无特殊偏好"
    weak_text = f"薄弱知识点: {', '.join(weak_points)}" if weak_points else "暂无薄弱点记录"

    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-8:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": QUIZ_GENERATOR_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

对话历史（请结合上下文理解用户意图）:
{history_text if history_text else "无历史记录"}

学习内容摘要:
{content_summary}

{pref_text}
{weak_text}

请根据以上信息生成练习题目，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [题目生成智能体] 正在调用 LLM 生成题目...")
        _emit_thinking_start("题目生成智能体", "")
        result = llm.chat_json_stream(messages, on_chunk=_emit_thinking_chunk, max_tokens=4096)
        record_from_mimo(llm, state.get("user_id", 0), "quiz_generation", state.get("task_id"))
        questions = result.get("questions", [])

        logger.info(f"  [题目生成智能体] 题目生成完成!")
        logger.info(f"    测验标题: {result.get('quiz_title', '未命名')}")
        logger.info(f"    题目数量: {len(questions)}")
        for i, q in enumerate(questions):
            qtype = q.get("question_type", "unknown")
            qtext = q.get("question_text", "")[:50]
            diff = q.get("difficulty", 3)
            logger.info(f"      题目{i+1} [{qtype}] 难度{diff}: {qtext}...")
        dist = result.get("difficulty_distribution", {})
        logger.info(f"    难度分布: 简单={dist.get('easy', 0)}, 中等={dist.get('medium', 0)}, 困难={dist.get('hard', 0)}")
        logger.info(f"{'='*60}")

        return {
            "quiz_questions": questions,
            "quiz_config": {
                "title": result.get("quiz_title", ""),
                "description": result.get("description", ""),
                "total": result.get("total_questions", len(questions)),
            },
            "current_step": f"题目生成智能体: 已生成 {len(questions)} 道题目",
            "stream_events": [{
                "event_type": "quiz",
                "agent": "quiz_generator",
                "data": result,
                "step_description": f"已生成 {len(questions)} 道练习题"
            }],
        }

    except Exception as e:
        logger.error(f"  [题目生成智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"题目生成失败: {str(e)}",
            "current_step": f"题目生成智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "quiz_generator",
                "data": {"error": str(e)},
                "step_description": "题目生成失败"
            }],
        }
