"""
画像构建 API - SSE 流式输出（background thread 模式）
通过自然语言对话构建用户画像

使用完整的 learning_graph（主控智能体意图分发 -> 各智能体处理），
主控会根据用户意图自动路由：简答/任务分解/RAG/题目生成等

前端调用: GET /api/ai/profile/chat?ticket=...&message=...&session_id=...

采用 background thread 模式：图执行在独立线程中运行，SSE 流从共享队列读取事件。
客户端断开后线程继续执行，画像更新和对话记录不会丢失。
"""
import json
import asyncio
import logging
import threading
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState
from app.schemas.sse_bridge import graph_step_to_sse, _sse
from app.services.stream_state import update_stream_text, mark_stream_done, mark_stream_error
from app.agents.profile_maintainer import profile_maintainer_node

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
    画像构建对话 - SSE 流式输出（background thread 模式）
    """
    # 验证 ticket（同步调用，放到线程池）
    try:
        ticket_info = await asyncio.to_thread(java_client.validate_ticket, ticket)
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

    # 获取已有画像（同步调用，放到线程池）
    user_profile = {}
    try:
        user_profile = await asyncio.to_thread(java_client.get_user_profile, user_id)
    except Exception:
        pass

    # 获取对话历史（按计划隔离，同步调用放到线程池）
    plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else None
    chat_history = []
    try:
        history = await asyncio.to_thread(
            java_client.get_dialogue_history, user_id, plan_id=plan_id_int, session_id=session_id, limit=30
        )
        for h in history:
            chat_history.append({
                "role": "user" if h.get("dialogueType") == "USER" else "assistant",
                "content": h.get("conversationText", ""),
            })
    except Exception:
        pass

    # 记录用户消息（同步调用，放到线程池）
    try:
        await asyncio.to_thread(
            java_client.create_dialogue,
            user_id, session_id, message, "USER", None, "profile",
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
        "rag_poor_module_ids": [],
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

    # ─── background thread 模式 ───
    bg_state = {
        "events": [],           # 待推送的 SSE 事件字符串
        "finished": False,      # 图执行是否完成
        "error": None,          # 异常信息
        "ai_response_parts": [],  # AI 回复片段
        "profile_update_needed": False,
    }

    def _sse_callback(data: str):
        """实时回调：节点执行期间直接推送事件到队列"""
        bg_state["events"].append(data)

    initial_state["sse_callback"] = _sse_callback

    def _run_graph_sync():
        """同步执行图工作流（在独立线程中运行，不阻塞事件循环）"""
        # 标记流式开始（即使还没生成文本，前端也能检测到后端在处理）
        update_stream_text(session_id, "", "profile")
        try:
            async def _run():
                graph = get_learning_graph()
                logger.info(f"[画像构建] 图执行开始 (线程: {threading.current_thread().name})")
                config = {"configurable": {"thread_id": session_id}}
                async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_output is None:
                            continue
                        if node_output.get("profile_update_needed"):
                            bg_state["profile_update_needed"] = True
                        for sse_data in graph_step_to_sse(node_name, node_output):
                            bg_state["events"].append(sse_data)
                            _persist_profile_update(sse_data, user_id)
                            if '"node_content"' in sse_data:
                                try:
                                    d = json.loads(sse_data.replace("data: ", "").strip())
                                    content = d.get("content", "")
                                    if content:
                                        bg_state["ai_response_parts"].append(content)
                                        accumulated = "".join(bg_state["ai_response_parts"])
                                        update_stream_text(session_id, accumulated, "profile")
                                except Exception:
                                    pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())

            # 简答智能体检测到画像信息时，后台执行画像维护
            if bg_state["profile_update_needed"]:
                threading.Thread(
                    target=_bg_profile_maintenance,
                    args=(user_id, message, chat_history, user_profile),
                    daemon=True,
                ).start()

            # 推送完成事件
            bg_state["events"].append(_sse({"type": "done"}))

        except Exception as e:
            logger.error(f"[画像构建] 图执行异常: {e}", exc_info=True)
            bg_state["error"] = str(e)
            mark_stream_error(session_id, str(e))
            bg_state["events"].append(_sse({"type": "error", "content": str(e)}))

        finally:
            mark_stream_done(session_id)
            # 无论客户端是否断开，都保存 AI 回复到数据库
            ai_response = "\n".join(bg_state["ai_response_parts"]) if bg_state["ai_response_parts"] else "处理完成"
            if ai_response:
                try:
                    java_client.create_dialogue(
                        user_id=user_id,
                        session_id=session_id,
                        conversation_text=ai_response,
                        dialogue_type="AI",
                        intent_type="profile",
                    )
                    logger.info(f"[画像构建] AI 回复已保存 (长度: {len(ai_response)})")
                except Exception as e:
                    logger.warning(f"[画像构建] 记录 AI 回复失败: {e}")
            bg_state["finished"] = True

    # 启动独立线程执行图工作流（不阻塞事件循环，SSE 可实时推送）
    threading.Thread(target=_run_graph_sync, daemon=True).start()

    async def stream():
        """SSE 流：从共享队列读取事件并推送给客户端"""
        logger.info(f"[画像构建] stream() 开始, 后台线程已启动")
        event_count = 0
        try:
            while True:
                if bg_state["events"]:
                    sse_data = bg_state["events"].pop(0)
                    if sse_data:
                        event_count += 1
                        yield sse_data
                elif bg_state["finished"]:
                    break
                else:
                    await asyncio.sleep(0.05)
            logger.info(f"[画像构建] stream() 结束, 共 {event_count} 个事件")
        except GeneratorExit:
            logger.warning(f"[画像构建] 客户端断开, 已推送 {event_count} 个事件, 后台线程继续执行")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _bg_profile_maintenance(user_id: int, user_message: str, chat_history: list, user_profile: dict):
    """后台画像维护：简答智能体检测到画像信息后触发"""
    try:
        logger.info(f"[画像维护] 开始更新用户 {user_id} 的画像")
        state = {
            "user_message": user_message,
            "chat_history": chat_history,
            "user_profile": user_profile,
        }
        result = profile_maintainer_node(state)
        if result.get("stream_events"):
            for event in result["stream_events"]:
                if event.get("event_type") == "profile_update":
                    updated_behavior = event.get("data", {}).get("updated_behavior", {})
                    reason = event.get("data", {}).get("reason", "对话画像自动更新")
                    if updated_behavior:
                        java_client.save_user_profile(user_id, updated_behavior, reason)
                        logger.info(f"[画像维护] 用户 {user_id} 画像更新成功")
        else:
            logger.info(f"[画像维护] 用户 {user_id} 无需更新画像")
    except Exception as e:
        logger.error(f"[画像维护] 更新失败: {str(e)}", exc_info=True)


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    yield _sse({"type": "error", "content": message})


def _persist_profile_update(sse_data: str, user_id: int):
    """从 SSE 事件中提取画像更新并持久化到数据库"""
    try:
        if '"profile_update"' not in sse_data:
            return
        d = json.loads(sse_data.replace("data: ", "").strip())
        if d.get("type") != "profile_update":
            return
        dimensions = d.get("dimensions", {})
        updated_behavior = dimensions.get("updated_behavior")
        if not updated_behavior:
            return
        reason = dimensions.get("reason", "画像构建自动更新")
        logger.info(f"[画像持久化] 保存用户 {user_id} 的画像更新: {reason}")
        java_client.save_user_profile(user_id, updated_behavior, reason)
        logger.info(f"[画像持久化] 画像保存成功")
    except Exception as e:
        logger.warning(f"[画像持久化] 保存失败: {e}")
