"""
多智能体对话 API - SSE 流式输出
支持人机协同实时优化、前端可视化实时流式输出
"""
import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.agents.schemas import ChatRequest, AgentState, NODE_HUMAN_CONFIRM
from app.agents.conversation_compressor import build_chat_history_with_context, async_compress_and_save
from app.graph.learning_graph import get_learning_graph
from app.services.db.java_client import java_client

logger = logging.getLogger("api.agent_chat")
router = APIRouter()


@router.post("/chat")
async def agent_chat(request: ChatRequest):
    """
    多智能体对话入口 - SSE 流式输出
    前端通过 EventSource 或 fetch + ReadableStream 接收实时事件
    """
    logger.info(f"{'#'*60}")
    logger.info(f"  [API] 收到对话请求")
    logger.info(f"  用户ID: {request.user_id}, 计划ID: {request.plan_id}")
    logger.info(f"  会话ID: {request.session_id}")
    logger.info(f"  消息: {request.message[:100]}")
    logger.info(f"{'#'*60}")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # 1. 获取用户画像
            logger.info(f"  [API] 正在获取用户画像...")
            user_profile = {}
            try:
                user_profile = java_client.get_user_profile(request.user_id)
                logger.info(f"  [API] 用户画像获取成功: 领域={user_profile.get('domain', '未知')}")
            except Exception as e:
                logger.warning(f"  [API] 用户画像获取失败: {str(e)}")

            # 2. 获取对话历史（带压缩上下文）
            logger.info(f"  [API] 正在获取对话历史...")
            chat_history = []
            try:
                from app.agents.conversation_compressor import build_chat_history_with_context
                history = java_client.get_dialogue_history(
                    user_id=request.user_id,
                    plan_id=request.plan_id,
                    session_id=request.session_id,
                    limit=200,
                )
                chat_history = build_chat_history_with_context(history)
                logger.info(f"  [API] 获取对话历史: {len(chat_history)} 条")
            except Exception as e:
                logger.warning(f"  [API] 对话历史获取失败: {str(e)}")

            # 3. 记录用户消息到 Java 后端
            logger.info(f"  [API] 正在记录用户消息...")
            try:
                java_client.create_dialogue(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    conversation_text=request.message,
                    dialogue_type="USER",
                    plan_id=request.plan_id,
                )
                logger.info(f"  [API] 用户消息记录成功")
            except Exception as e:
                logger.warning(f"  [API] 用户消息记录失败: {str(e)}")

            # 4. 构造初始状态
            initial_state: AgentState = {
                "user_id": request.user_id,
                "plan_id": request.plan_id,
                "session_id": request.session_id,
                "user_message": request.message,
                "human_feedback": request.human_feedback,
                "chat_history": chat_history,
                "user_profile": user_profile,
                "intent": "",
                "next_node": "",
                "needs_human_confirm": False,
                "profile_update_needed": False,
                "learning_goal": request.message,
                "task_breakdown": None,
                "task_breakdown_confirmed": False,
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

            # 5. 执行工作流图
            logger.info(f"  [API] 正在执行工作流图...")
            graph = get_learning_graph()

            yield _sse_event({
                "event_type": "thinking",
                "agent": "system",
                "data": {"message": "开始处理..."},
                "step_description": "系统初始化"
            })

            all_events = []
            ai_response_parts = []
            node_count = 0
            raw_sse_queue = []

            # 注入 sse_callback，使智能体的流式 JSON 输出能实时推送
            initial_state["sse_callback"] = lambda data: raw_sse_queue.append(data)

            config = {"configurable": {"thread_id": request.session_id}}
            async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                # 先推送 sse_callback 收集的实时事件（如 raw_chunk）
                while raw_sse_queue:
                    yield raw_sse_queue.pop(0)

                for node_name, node_output in event.items():
                    if node_output is None or not isinstance(node_output, dict):
                        continue

                    node_count += 1
                    logger.info(f"  [API] 节点执行完成: {node_name} (第{node_count}个)")

                    stream_events = node_output.get("stream_events", [])
                    for evt in stream_events:
                        all_events.append(evt)
                        yield _sse_event(evt)

                        if evt.get("event_type") == "content":
                            text = evt.get("data", {}).get("text", "")
                            if text:
                                ai_response_parts.append(text)

                        # 持久化画像更新
                        if evt.get("event_type") == "profile_update":
                            _persist_profile_update_raw(evt, request.user_id)

                    # 节点完成后也推送可能残留的 sse_callback 事件
                    while raw_sse_queue:
                        yield raw_sse_queue.pop(0)

                    step = node_output.get("current_step", "")
                    if step:
                        yield _sse_event({
                            "event_type": "thinking",
                            "agent": node_name,
                            "data": {"step": step},
                            "step_description": step
                        })

                    if node_output.get("needs_human_confirm"):
                        logger.info(f"  [API] 需要用户确认")
                        yield _sse_event({
                            "event_type": "confirm_needed",
                            "agent": "system",
                            "data": {
                                "message": "请确认或补充说明",
                                "task_breakdown": node_output.get("task_breakdown"),
                            },
                            "step_description": "等待用户确认"
                        })

            logger.info(f"  [API] 工作流图执行完成，共 {node_count} 个节点")

            # 6. 记录 AI 回复到 Java 后端
            ai_response = "\n".join(ai_response_parts) if ai_response_parts else "处理完成"
            logger.info(f"  [API] AI 回复长度: {len(ai_response)} 字符")
            try:
                intent_type = None
                for evt in all_events:
                    if evt.get("event_type") == "task_breakdown":
                        intent_type = "task_breakdown"
                    elif evt.get("event_type") == "module":
                        intent_type = "resource_generated"
                    elif evt.get("event_type") == "quiz":
                        intent_type = "quiz_generated"

                java_client.create_dialogue(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    conversation_text=ai_response,
                    dialogue_type="AI",
                    plan_id=request.plan_id,
                    intent_type=intent_type,
                )
                logger.info(f"  [API] AI 回复记录成功")
            except Exception as e:
                logger.warning(f"  [API] AI 回复记录失败: {str(e)}")

            # 7. 会话压缩任务（异步后台）
            asyncio.create_task(async_compress_and_save(
                user_id=request.user_id,
                session_id=request.session_id,
                plan_id=request.plan_id or 0,
            ))

            yield _sse_event({
                "event_type": "done",
                "agent": "system",
                "data": {"message": "处理完成"},
                "step_description": "完成"
            })
            logger.info(f"  [API] 流式响应完成")

        except Exception as e:
            logger.error(f"  [API] 系统错误: {str(e)}", exc_info=True)
            yield _sse_event({
                "event_type": "error",
                "agent": "system",
                "data": {"error": str(e)},
                "step_description": f"系统错误: {str(e)}"
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/confirm")
async def confirm_task(request: ChatRequest):
    """
    用户确认/补充任务分解 - SSE 流式输出
    """
    logger.info(f"{'#'*60}")
    logger.info(f"  [API] 收到确认请求")
    logger.info(f"  用户ID: {request.user_id}, 消息: {request.message[:100]}")
    logger.info(f"{'#'*60}")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            user_profile = {}
            try:
                user_profile = java_client.get_user_profile(request.user_id)
            except Exception as e:
                logger.warning(f"  [API] 用户画像获取失败: {str(e)}")

            chat_history = []
            try:
                history = java_client.get_dialogue_history(
                    user_id=request.user_id,
                    plan_id=request.plan_id,
                    session_id=request.session_id,
                    limit=200,
                )
                chat_history = build_chat_history_with_context(history)
            except Exception:
                pass

            try:
                java_client.create_dialogue(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    conversation_text=request.message,
                    dialogue_type="USER",
                    plan_id=request.plan_id,
                    intent_type="confirm",
                )
            except Exception:
                pass

            graph = get_learning_graph()
            config = {"configurable": {"thread_id": request.session_id}}

            yield _sse_event({
                "event_type": "thinking",
                "agent": "system",
                "data": {"message": "处理确认/补充..."},
                "step_description": "处理用户反馈"
            })

            all_events = []
            ai_response_parts = []
            raw_sse_queue = []

            # 原生 Checkpointer：更新运行状态（注入新连接的 sse_callback 并写入用户反馈）
            new_callback = lambda data: raw_sse_queue.append(data)
            await graph.aupdate_state(config, {
                "human_feedback": request.message,
                "sse_callback": new_callback
            }, as_node=NODE_HUMAN_CONFIRM)

            logger.info(f"  [API] 从 Checkpointer 恢复工作流运行 (Session: {request.session_id})")

            async for event in graph.astream(None, config=config, stream_mode="updates"):
                # 先推送 sse_callback 收集的实时事件（如 raw_chunk）
                while raw_sse_queue:
                    yield raw_sse_queue.pop(0)

                for node_name, node_output in event.items():
                    if node_output is None or not isinstance(node_output, dict):
                        continue
                    stream_events = node_output.get("stream_events", [])
                    for evt in stream_events:
                        all_events.append(evt)
                        yield _sse_event(evt)
                        if evt.get("event_type") == "content":
                            text = evt.get("data", {}).get("text", "")
                            if text:
                                ai_response_parts.append(text)
                        # 持久化画像更新
                        if evt.get("event_type") == "profile_update":
                            _persist_profile_update_raw(evt, request.user_id)

                    # 节点完成后也推送可能残留的 sse_callback 事件
                    while raw_sse_queue:
                        yield raw_sse_queue.pop(0)

                    step = node_output.get("current_step", "")
                    if step:
                        yield _sse_event({
                            "event_type": "thinking",
                            "agent": node_name,
                            "data": {"step": step},
                            "step_description": step
                        })

            ai_response = "\n".join(ai_response_parts) if ai_response_parts else "处理完成"
            try:
                java_client.create_dialogue(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    conversation_text=ai_response,
                    dialogue_type="AI",
                    plan_id=request.plan_id,
                )
            except Exception:
                pass

            # 会话压缩任务（异步后台）
            asyncio.create_task(async_compress_and_save(
                user_id=request.user_id,
                session_id=request.session_id,
                plan_id=request.plan_id or 0,
            ))

            yield _sse_event({
                "event_type": "done",
                "agent": "system",
                "data": {"message": "处理完成"},
                "step_description": "完成"
            })

        except Exception as e:
            logger.error(f"  [API] 确认处理错误: {str(e)}", exc_info=True)
            yield _sse_event({
                "event_type": "error",
                "agent": "system",
                "data": {"error": str(e)},
                "step_description": f"系统错误: {str(e)}"
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _sse_event(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _persist_profile_update_raw(evt: dict, user_id: int):
    """从原始 graph 事件中提取画像更新并持久化到数据库"""
    try:
        data = evt.get("data", {})
        # 使用 updated_behavior（完整合并后的画像），而非 updates（原始增量，会导致数据丢失）
        updated_behavior = data.get("updated_behavior")
        if not updated_behavior:
            return
        reason = data.get("reason", "对话分析自动更新")
        logger.info(f"[画像持久化] 保存用户 {user_id} 的画像更新: {reason}")
        java_client.save_user_profile(user_id, updated_behavior, reason)
        logger.info(f"[画像持久化] 画像保存成功")
    except Exception as e:
        logger.warning(f"[画像持久化] 保存失败: {e}")
