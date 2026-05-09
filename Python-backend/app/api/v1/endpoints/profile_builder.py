"""
画像构建 API - SSE 流式输出
通过自然语言对话构建用户画像

使用完整的 learning_graph（主控智能体意图分发 -> 各智能体处理），
主控会根据用户意图自动路由：简答/任务分解/RAG/题目生成等

前端调用: GET /api/ai/profile/chat?ticket=...&message=...&session_id=...
"""
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState
from app.schemas.sse_bridge import graph_step_to_sse, _sse

logger = logging.getLogger("api.profile_builder")
router = APIRouter()


@router.get("/chat")
async def profile_chat(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    message: str = Query(..., description="用户消息"),
    session_id: str = Query(..., description="会话 ID"),
    plan_id: str = Query("", description="学习计划 ID（可选，用于限定对话范围）"),
    task_breakdown: str = Query("", description="前端回传的任务分解 JSON（确认时）"),
):
    """
    画像构建对话 - SSE 流式输出
    使用完整 graph 流程: 主控智能体 -> 意图分发 -> 各智能体处理
    """
    # 验证 ticket
    try:
        ticket_info = java_client.validate_ticket(ticket)
        user_id = ticket_info["user_id"]
    except Exception as e:
        logger.error(f"Ticket 验证失败: {e}")
        return StreamingResponse(
            _error_stream(f"认证失败: {str(e)}"),
            media_type="text/event-stream",
        )

    logger.info(f"[画像构建] 用户 {user_id}, 会话 {session_id}, 消息: {message[:50]}")

    # 解析前端回传的任务分解
    parsed_breakdown = None
    breakdown_confirmed = False
    if task_breakdown:
        try:
            parsed_breakdown = json.loads(task_breakdown)
            breakdown_confirmed = True
        except Exception as e:
            logger.warning(f"[画像构建] 解析 task_breakdown 失败: {e}")

    # 获取已有画像
    user_profile = {}
    try:
        user_profile = java_client.get_user_profile(user_id)
    except Exception:
        pass

    # 获取对话历史（按计划隔离）
    plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else None
    chat_history = []
    try:
        history = java_client.get_dialogue_history(user_id=user_id, plan_id=plan_id_int, limit=30)
        for h in history:
            chat_history.append({
                "role": "user" if h.get("dialogueType") == "USER" else "assistant",
                "content": h.get("conversationText", ""),
            })
    except Exception:
        pass

    # 记录用户消息
    try:
        java_client.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            conversation_text=message,
            dialogue_type="USER",
            intent_type="profile",
        )
    except Exception as e:
        logger.warning(f"记录用户消息失败: {e}")

    # 构造 AgentState - 使用完整 graph
    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": None,
        "session_id": session_id,
        "user_message": message,
        "human_feedback": None,
        "chat_history": chat_history,
        "user_profile": user_profile,
        "intent": "",
        "next_node": "",
        "needs_human_confirm": False,
        "profile_update_needed": False,
        "learning_goal": message,
        "task_breakdown": parsed_breakdown,
        "task_breakdown_confirmed": breakdown_confirmed,
        "search_queries": [],
        "rag_results": [],
        "rag_context_chunks": [],
        "rag_sufficient": False,
        "retrieval_config": {},
        "review_passed": True,
        "review_feedback": "",
        "review_suggestions": [],
        "orchestrated_content": None,
        "module_list": [],
        "generated_content": None,
        "quiz_config": None,
        "quiz_questions": None,
        "quiz_answer": None,
        "quiz_result": None,
        "stream_events": [],
        "current_step": "",
        "error": None,
        "iteration_count": 0,
        "max_iterations": 15,
        "accumulated_context": "",
    }

    async def stream():
        ai_response_parts = []
        try:
            graph = get_learning_graph()
            async for event in graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data
                        if '"chunk"' in sse_data:
                            try:
                                d = json.loads(sse_data.replace("data: ", "").strip())
                                ai_response_parts.append(d.get("content", ""))
                            except Exception:
                                pass

            yield _sse({"type": "done"})

        except Exception as e:
            logger.error(f"画像构建流异常: {e}", exc_info=True)
            yield _sse({"type": "error", "content": str(e)})

        # 记录 AI 回复
        ai_response = "\n".join(ai_response_parts) if ai_response_parts else "处理完成"
        if ai_response:
            try:
                java_client.create_dialogue(
                    user_id=user_id,
                    session_id=session_id,
                    conversation_text=ai_response,
                    dialogue_type="AI",
                    intent_type="profile",
                )
            except Exception as e:
                logger.warning(f"记录 AI 回复失败: {e}")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    yield _sse({"type": "error", "content": message})
