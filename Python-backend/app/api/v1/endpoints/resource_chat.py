"""
资源对话 API - SSE 流式输出
桥接前端 /api/ai/* 请求与现有 LangGraph 多智能体系统

前端调用:
  GET /api/ai/chat?ticket=...&plan_id=...&message=...&session_id=...
  GET /api/ai/resource/generate?ticket=...&plan_id=...&module_id=...&type=...

使用现有的 learning_graph（11 节点 StateGraph）处理请求，
通过 sse_bridge 将 graph 事件翻译为前端期望的 SSE 格式
"""
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState
from app.schemas.sse_bridge import graph_step_to_sse

logger = logging.getLogger("api.resource_chat")
router = APIRouter()


@router.get("/chat")
async def plan_chat(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    plan_id: str = Query(..., description="学习计划 ID"),
    message: str = Query(..., description="用户消息"),
    session_id: str = Query("", description="会话 ID"),
    task_breakdown: str = Query("", description="前端回传的任务分解 JSON（确认时）"),
):
    """
    计划关联 AI 对话 - SSE 流式输出
    使用现有 learning_graph 的完整多智能体工作流
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

    plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else 0

    # 解析前端回传的任务分解
    parsed_breakdown = None
    breakdown_confirmed = False
    if task_breakdown:
        try:
            parsed_breakdown = json.loads(task_breakdown)
            breakdown_confirmed = True
            logger.info(f"[计划对话] 收到前端回传的任务分解: {len(parsed_breakdown.get('modules', []))} 个模块")
        except Exception as e:
            logger.warning(f"[计划对话] 解析 task_breakdown 失败: {e}")

    if not session_id:
        session_id = f"chat-{plan_id}-{user_id}"

    logger.info(f"[计划对话] 用户 {user_id}, 计划 {plan_id}, 会话 {session_id}")
    logger.info(f"[计划对话] 消息: {message[:100]}")

    # 获取用户画像
    user_profile = {}
    try:
        user_profile = java_client.get_user_profile(user_id)
    except Exception:
        pass

    # 获取对话历史（按计划隔离）
    chat_history = []
    try:
        history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id_int, limit=30
        )
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
            plan_id=plan_id_int,
        )
    except Exception as e:
        logger.warning(f"记录用户消息失败: {e}")

    # 构造现有 graph 的初始状态
    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id_int,
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
                    # 使用 sse_bridge 翻译 graph 事件为前端格式
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data
                        # 收集 AI 回复文本
                        if '"chunk"' in sse_data:
                            try:
                                d = json.loads(sse_data.replace("data: ", "").strip())
                                ai_response_parts.append(d.get("content", ""))
                            except Exception:
                                pass

            yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'

        except Exception as e:
            logger.error(f"对话流异常: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'

        # 记录 AI 回复
        ai_response = "\n".join(ai_response_parts) if ai_response_parts else "处理完成"
        if ai_response:
            try:
                java_client.create_dialogue(
                    user_id=user_id,
                    session_id=session_id,
                    conversation_text=ai_response,
                    dialogue_type="AI",
                    plan_id=plan_id,
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


@router.get("/resource/generate")
async def generate_single_resource(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    plan_id: str = Query(..., description="学习计划 ID"),
    module_id: str = Query(..., description="模块 ID"),
    type: str = Query("document", description="资源类型: document/mindmap/quiz/code/video"),
    title: str = Query("", description="模块标题"),
    description: str = Query("", description="模块描述"),
):
    """
    单资源生成 - SSE 流式输出
    使用现有 learning_graph，以 generate_resource 意图进入，
    图会自动走: 主控 -> 任务分解(可选) -> RAG检索 -> 审查 -> 编排
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

    plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else 0
    module_id_int = int(module_id) if module_id and module_id.isdigit() else 0

    logger.info(f"[资源生成] 用户 {user_id}, 计划 {plan_id_int}, 模块 {module_id_int}")
    logger.info(f"[资源生成] 类型: {type}, 标题: {title}")

    # 获取用户画像
    user_profile = {}
    try:
        user_profile = java_client.get_user_profile(user_id)
    except Exception:
        pass

    # 更新计划状态为"生成中"
    try:
        java_client.update_plan_status(plan_id_int, 1)
    except Exception:
        pass

    # 构造以资源生成为目标的初始状态
    resource_message = f"请为以下模块生成{type}类型的学习资源: {title}"
    if description:
        resource_message += f"\n模块描述: {description}"

    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id_int,
        "session_id": f"resource-{plan_id_int}-{module_id_int}",
        "user_message": resource_message,
        "human_feedback": None,
        "chat_history": [],
        "user_profile": user_profile,
        "intent": "generate_resource",
        "next_node": "rag_retriever",  # 直接进入 RAG 检索
        "needs_human_confirm": False,
        "profile_update_needed": False,
        "learning_goal": resource_message,
        "task_breakdown": {
            "modules": [{
                "module_id": module_id,
                "title": title,
                "description": description,
                "resources": [{"resource_type": type}],
            }]
        },
        "task_breakdown_confirmed": True,
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
        "max_iterations": 10,
        "accumulated_context": "",
    }

    async def stream():
        try:
            graph = get_learning_graph()
            async for event in graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data

            yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'

        except Exception as e:
            logger.error(f"资源生成流异常: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'

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
    yield f'data: {json.dumps({"type": "error", "content": message}, ensure_ascii=False)}\n\n'
