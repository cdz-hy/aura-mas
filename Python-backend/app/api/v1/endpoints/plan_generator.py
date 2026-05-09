"""
计划生成 API - SSE 流式输出
根据学习目标和用户画像生成个性化学习计划

使用现有的 task_decomposer_node 生成学习路径

前端调用: GET /api/ai/plan/generate?ticket=...&goal=...&plan_id=...
"""
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.agents.task_decomposer import task_decomposer_node
from app.agents.schemas import AgentState
from app.schemas.sse_bridge import graph_step_to_sse, _sse

logger = logging.getLogger("api.plan_generator")
router = APIRouter()


@router.get("/generate")
async def plan_generate(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    goal: str = Query(..., description="学习目标"),
    plan_id: int = Query(..., description="学习计划 ID"),
):
    """
    学习计划生成 - SSE 流式输出
    使用现有 task_decomposer_node 生成个性化学习路径
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

    logger.info(f"[计划生成] 用户 {user_id}, 计划 {plan_id}, 目标: {goal[:50]}")

    # 获取用户画像
    user_profile = {}
    try:
        user_profile = java_client.get_user_profile(user_id)
    except Exception:
        pass

    # 获取对话历史
    chat_history = []
    try:
        history = java_client.get_dialogue_history(user_id=user_id, limit=10)
        for h in history:
            chat_history.append({
                "role": "user" if h.get("dialogueType") == "USER" else "assistant",
                "content": h.get("conversationText", ""),
            })
    except Exception:
        pass

    # 更新计划状态为"生成中"
    try:
        java_client.update_plan_status(plan_id, 1)
    except Exception as e:
        logger.warning(f"更新计划状态失败: {e}")

    # 构造 AgentState
    state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id,
        "session_id": f"plan-{plan_id}",
        "user_message": goal,
        "human_feedback": None,
        "chat_history": chat_history,
        "user_profile": user_profile,
        "intent": "generate_resource",
        "next_node": "task_decomposer",
        "needs_human_confirm": False,
        "profile_update_needed": False,
        "learning_goal": goal,
        "task_breakdown": None,
        "task_breakdown_confirmed": False,
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
        "max_iterations": 5,
        "accumulated_context": "",
    }

    async def stream():
        try:
            # 调用现有 task_decomposer_node
            node_output = task_decomposer_node(state)

            # 翻译并发送事件
            for sse_data in graph_step_to_sse("task_decomposer", node_output):
                yield sse_data

            # 提取 task_breakdown 数据作为 plan 事件发送
            task_breakdown = node_output.get("task_breakdown")
            if task_breakdown:
                plan_data = {**task_breakdown, "id": plan_id}
                yield _sse({"type": "plan", "data": plan_data})

            yield _sse({"type": "done"})

        except Exception as e:
            logger.error(f"计划生成流异常: {e}", exc_info=True)
            yield _sse({"type": "error", "content": str(e)})

        # 更新计划状态为"用户确认中"
        try:
            java_client.update_plan_status(plan_id, 2)
        except Exception as e:
            logger.warning(f"更新计划状态失败: {e}")

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
