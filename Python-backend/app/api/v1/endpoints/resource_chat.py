"""
资源对话 API - SSE 流式输出
桥接前端 /api/ai/* 请求与 LangGraph 多智能体系统

前端调用:
  GET /api/ai/chat?ticket=...&plan_id=...&message=...&session_id=...&task_breakdown=...
  GET /api/ai/resource/generate?ticket=...&plan_id=...&module_id=...&type=...

/chat 端点支持两种执行模式:
  1. 新建模式：首次对话，构造 initial_state 从头执行图（interrupt 在 human_confirm 暂停）
  2. 恢复模式：确认/补充时，检测 checkpointer 中断状态，通过 aupdate_state + astream(None) 恢复
"""
import json
import logging
import asyncio
import threading
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState, NODE_RESOURCE_TYPE_GENERATOR, NODE_ANIMATION_SKILL_GENERATOR, NODE_HUMAN_CONFIRM
from app.prompts import QUIZ_GRADER_PROMPT
from app.agents.profile_maintainer import profile_maintainer_node
from app.agents.conversation_compressor import build_chat_history_with_context, async_compress_and_save
from app.schemas.sse_bridge import graph_step_to_sse
from app.utils.profile_utils import ensure_learning_behavior_fields
from app.utils.token_recorder import record_from_mimo
from app.services.stream_state import update_stream_text, mark_stream_done, mark_stream_error, request_stop, check_stop, clear_stop
from app.utils import stream_registry

logger = logging.getLogger("api.resource_chat")
router = APIRouter()


def _is_confirmation_message(message: str) -> bool:
    """
    判断用户输入的消息是否为对任务分解的确认，防止将含有“行”、“可以”等字眼的反馈（如“两个模块就行！”）误判为确认。
    """
    msg = message.strip()
    if msg == "确认，开始生成学习资源":
        return True
    
    # 预处理：转小写，去掉常用标点和末尾语气词
    clean_msg = msg.lower().strip("!.，。！？~")
    
    # 1. 排除明显的修改、拒绝或调整关键词
    exclude_words = ["不", "多", "少", "改", "重", "加", "减", "删", "调整", "优化"]
    if any(ew in clean_msg for ew in exclude_words):
        return False
    if "太" in clean_msg and "太棒了" not in clean_msg:
        return False
        
    # 2. 确认词集合
    confirm_words = {
        "确认", "可以", "没问题", "同意", "好的", "ok", "行", "嗯", "就这个", "就这", 
        "挺好", "没意见", "想要这种", "要这种", "就要这种", "真tm是天才", "天才", 
        "牛逼", "完美", "极好", "太棒了", "可以的", "好的呢", "没问题哈", "行啊", 
        "行呀", "好的呀", "行吧", "就这吧", "就这样", "谢谢", "谢了", "thx"
    }
    
    # 分割输入以支持如“好的，没问题”之类组合词
    parts = [p.strip() for p in clean_msg.replace("，", ",").replace("、", ",").split(",")]
    if parts and all(p in confirm_words for p in parts if p):
        return True
        
    return False



def _update_bg_state_from_node(bg_state, node_output, node_name, plan_id_int, user_id, session_id, emit=None):
    """从节点输出更新 bg_state（资源持久化、状态追踪）
    emit: 可选回调，用于实时推送 SSE 事件（线程安全版本的 sse_callback）
    """
    if not isinstance(node_output, dict):
        return
    _emit = emit or bg_state["events"].append
    if node_output.get("orchestrated_content"):
        bg_state["orchestrated_content"] = node_output["orchestrated_content"]
    if node_output.get("module_list"):
        bg_state["module_list"] = node_output["module_list"]
        if plan_id_int:
            for mod in node_output["module_list"]:
                if mod.get("content") and mod.get("module_order") not in bg_state["saved_module_orders"]:
                    mod_order = mod.get("module_order")
                    placeholder = bg_state["placeholder_map"].get(mod_order)
                    if placeholder:
                        try:
                            module_data = {
                                "title": mod.get("title", placeholder.get("title", "")),
                                "content": mod.get("content", ""),
                                "description": mod.get("description", ""),
                                "key_concepts": mod.get("metadata", {}).get("key_concepts", []) or mod.get("key_points", []),
                                "module_title": mod.get("title", ""),
                                "estimated_hours": mod.get("estimated_hours", 2),
                                "references": mod.get("references", []),
                            }
                            images = mod.get("images", [])
                            if images:
                                module_data["images"] = images
                            java_client.update_resource_content(
                                placeholder["id"],
                                json.dumps(module_data, ensure_ascii=False),
                                status=2,
                            )
                            try:
                                res_task = java_client.create_generation_task(
                                    plan_id=plan_id_int,
                                    resource_id=placeholder["id"],
                                    agent_chain="plan_chat",
                                )
                                if res_task and isinstance(res_task, dict):
                                    java_client.update_generation_task(res_task["id"], 2, update_resource_status=False)
                            except Exception as e:
                                logger.warning(f"[对话流] 创建资源 task 记录失败: {e}")
                            saved = {"id": placeholder["id"], "type": placeholder["type"], "title": mod.get("title", placeholder["title"])}
                            bg_state["generated_resource_info"].append(saved)
                            bg_state["saved_module_orders"].add(mod_order)
                            _emit(
                                f'data: {json.dumps({"type": "resource_stream_update", "resource": saved, "content": mod["content"]}, ensure_ascii=False)}\n\n'
                            )
                        except Exception as e:
                            logger.warning(f"[占位更新] 更新资源 {placeholder['id']} 失败: {e}")
                    else:
                        saved = _save_module_immediately(plan_id_int, mod)
                        if saved:
                            bg_state["generated_resource_info"].append(saved)
                            bg_state["saved_module_orders"].add(mod_order)
                            _emit(
                                f'data: {json.dumps({"type": "resource_stream_update", "resource": saved, "content": mod["content"]}, ensure_ascii=False)}\n\n'
                            )
    if node_output.get("quiz_questions"):
        bg_state["quiz_questions"] = node_output["quiz_questions"]
    if node_output.get("quiz_config"):
        bg_state["quiz_config"] = node_output["quiz_config"]
    if node_output.get("generated_content"):
        bg_state["generated_content"] = node_output["generated_content"]
    if node_output.get("profile_update_needed"):
        bg_state["profile_update_needed"] = True
    tb = node_output.get("task_breakdown")
    if tb and node_name == "task_decomposer":
        bg_state["new_breakdown"] = tb
    if "task_breakdown_confirmed" in node_output:
        bg_state["breakdown_confirmed"] = node_output["task_breakdown_confirmed"]
    if (node_name == "review_orchestrate"
            and not node_output.get("review_passed")
            and node_output.get("retry_module_ids")
            and node_output.get("passed_module_list")
            and plan_id_int
            and bg_state["breakdown_confirmed"]):
        passed_modules = node_output["passed_module_list"]
        failed_module_ids = node_output.get("retry_module_ids", [])
        for failed_id in failed_module_ids:
            placeholder = bg_state["placeholder_map"].get(failed_id)
            if placeholder:
                try:
                    java_client.update_resource_content(
                        placeholder["id"],
                        json.dumps({"title": placeholder["title"], "content": ""}, ensure_ascii=False),
                        status=3,
                    )
                    _emit(
                        f'data: {json.dumps({"type": "resource_stream_failed", "resource_id": placeholder["id"]}, ensure_ascii=False)}\n\n'
                    )
                    logger.info(f"[审查失败] 模块 {failed_id} 占位记录 {placeholder['id']} 已标记为失败")
                except Exception as e:
                    logger.warning(f"[审查失败] 更新占位记录失败: {e}")
        if passed_modules:
            unpassed = [m for m in passed_modules
                        if m.get("module_order") not in bg_state["saved_module_orders"]]
            if unpassed:
                new_ids = _save_modules_as_resources(plan_id_int, unpassed, None)
                for idx, rid in enumerate(new_ids):
                    mod = unpassed[idx] if idx < len(unpassed) else {}
                    bg_state["generated_resource_info"].append({
                        "id": rid,
                        "type": _normalize_module_type(mod.get("module_type", "text")),
                        "title": mod.get("title", f"模块 {idx + 1}"),
                    })
                    bg_state["saved_module_orders"].add(mod.get("module_order"))
                logger.info(f"[增量保存] 已保存 {len(unpassed)} 个无占位的通过模块")


def _collect_stream_text(sse_data: str, ai_response_parts: list, session_id: str) -> list:
    """从 SSE 事件中提取流式文本并更新 stream_state"""
    if '"chunk"' in sse_data or '"stream_text"' in sse_data:
        try:
            d = json.loads(sse_data.replace("data: ", "").strip())
            content = d.get("content", "")
            if content:
                ai_response_parts.append(content)
                accumulated = "".join(ai_response_parts)
                update_stream_text(session_id, accumulated, "chat")
        except Exception:
            pass
    return ai_response_parts


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
            is_confirm = _is_confirmation_message(message)
            breakdown_confirmed = is_confirm
            logger.info(f"[计划对话] 收到前端回传的任务分解: {len(parsed_breakdown.get('modules', []))} 个模块, 确认={breakdown_confirmed}")
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
        # 确保 learning_behavior 字段完整
        if "learning_behavior" in user_profile:
            user_profile["learning_behavior"] = ensure_learning_behavior_fields(
                user_profile["learning_behavior"]
            )
    except Exception:
        pass

    # 获取对话历史（按当前会话隔离，多取以支持压缩上下文）
    chat_history = []
    raw_history = []
    try:
        raw_history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id_int, session_id=session_id, limit=200
        )
        # 使用压缩上下文构建 chat_history（压缩摘要 + context 之后的所有实际对话）
        chat_history = build_chat_history_with_context(raw_history)
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
            intent_type="plan_chat",
        )
    except Exception as e:
        logger.warning(f"记录用户消息失败: {e}")

    human_feedback = None
    if not breakdown_confirmed and parsed_breakdown:
        human_feedback = message

    # 创建对话任务，用于关联 Token 消耗记录
    chat_task_id = None
    try:
        task_result = java_client.create_generation_task(
            plan_id=plan_id_int,
            resource_id=0,
        )
        chat_task_id = task_result.get("id") if isinstance(task_result, dict) else None
    except Exception:
        pass

    # ── 恢复路径检测：checkpointer 中是否有中断在 human_confirm 的状态 ──
    _can_resume = False
    graph = get_learning_graph()
    config = {"configurable": {"thread_id": session_id}}
    if breakdown_confirmed or human_feedback:
        try:
            existing = graph.get_state(config)
            if existing and existing.next and NODE_HUMAN_CONFIRM in existing.next:
                _can_resume = True
                logger.info(f"[计划对话] 检测到中断状态，将从 checkpointer 恢复")
        except Exception:
            pass

    if _can_resume:
        # ── 恢复路径：aupdate_state + astream(None) ──
        logger.info(f"[计划对话] 使用 LangGraph interrupt/resume 模式")

        placeholder_map = {}
        if breakdown_confirmed and parsed_breakdown and plan_id_int:
            modules = parsed_breakdown.get("modules", [])
            if modules:
                placeholder_map = _create_placeholder_resources(plan_id_int, modules)
                logger.info(f"[占位资源] 已创建 {len(placeholder_map)} 个占位记录")

        bg_state = {
            "events": [],
            "breakdown_confirmed": breakdown_confirmed,
            "ai_response_parts": [],
            "module_list": [],
            "orchestrated_content": None,
            "quiz_questions": None,
            "quiz_config": None,
            "generated_content": None,
            "new_breakdown": None,
            "generated_resource_info": [],
            "saved_module_orders": set(),
            "placeholder_map": placeholder_map,
        }

        async def event_stream() -> AsyncGenerator[str, None]:
            clear_stop(session_id)
            update_stream_text(session_id, "", "chat")
            _sentinel = object()
            _queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            # sse_callback 线程安全：从后台线程 put 到 async queue
            def _threadsafe_cb(data):
                loop.call_soon_threadsafe(_queue.put_nowait, data)

            # 注入占位回调（graph 节点内部调用）
            def _create_placeholder_callback(modules: list) -> dict:
                if not plan_id_int or not modules:
                    return {}
                ph_map = _create_placeholder_resources(plan_id_int, modules)
                if ph_map:
                    bg_state["placeholder_map"] = ph_map
                    stream_registry.update_placeholder_map(session_id, ph_map)
                    _threadsafe_cb(
                        f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(ph_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n'
                    )
                    logger.info(f"[占位回调-恢复] 创建 {len(ph_map)} 个占位记录")
                return ph_map

            # 注册 session 回调到全局注册表（绕过 checkpointer 序列化限制）
            stream_registry.register_session(
                session_id,
                sse_callback=_threadsafe_cb,
                create_placeholder_callback=_create_placeholder_callback,
                placeholder_resource_map=placeholder_map,
            )

            def _run_graph():
                """后台线程：执行 aupdate_state + astream，将节点事件送入 queue"""
                try:
                    async def _do_resume():
                        graph_inner = get_learning_graph()
                        logger.info(f"[对话流-恢复] 从 checkpointer 恢复 (session: {session_id})")

                        # 提前推送占位资源，避免前端流式界面无法初始化
                        if placeholder_map:
                            _threadsafe_cb(
                                f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(placeholder_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n'
                            )
                            logger.info(f"[对话流-恢复] 推送已创建的 {len(placeholder_map)} 个占位记录到前端")

                        await graph_inner.aupdate_state(config, {
                            "user_message": message,
                            "human_feedback": None if breakdown_confirmed else (human_feedback or message),
                            "task_breakdown_confirmed": breakdown_confirmed,
                            "needs_human_confirm": False,
                            "sse_callback": _threadsafe_cb,
                            "create_placeholder_callback": _create_placeholder_callback,
                            "placeholder_resource_map": placeholder_map,
                            "chat_history": chat_history,
                            "user_profile": user_profile,
                        })
                        async for event in graph_inner.astream(None, config=config, stream_mode="updates"):
                            if check_stop(session_id):
                                _threadsafe_cb(None)  # sentinel
                                return
                            for node_name, node_output in event.items():
                                if node_output is None or not isinstance(node_output, dict):
                                    continue
                                _update_bg_state_from_node(bg_state, node_output, node_name, plan_id_int, user_id, session_id, emit=_threadsafe_cb)
                                # module 事件已由 sse_callback 通过 resource_stream_text 实时推送，跳过避免重复
                                filtered_events = [e for e in node_output.get("stream_events", []) if e.get("event_type") != "module"]
                                filtered_output = {**node_output, "stream_events": filtered_events}
                                for sse_data in graph_step_to_sse(node_name, filtered_output):
                                    bg_state["ai_response_parts"] = _collect_stream_text(sse_data, bg_state["ai_response_parts"], session_id)
                                    _persist_profile_update(sse_data, user_id)
                                    _threadsafe_cb(sse_data)

                    asyncio.run(_do_resume())
                    _bg_save_resources(bg_state, plan_id_int, user_id, session_id, message, chat_history, user_profile, chat_task_id, emit=_threadsafe_cb)
                    _save_plain_text_reply(bg_state["breakdown_confirmed"], bg_state["generated_resource_info"],
                                           bg_state["ai_response_parts"], user_id, session_id, plan_id_int)
                except Exception as e:
                    logger.error(f"[对话流-恢复] 线程异常: {e}", exc_info=True)
                    mark_stream_error(session_id, str(e))
                    _threadsafe_cb(f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n')
                finally:
                    stream_registry.unregister_session(session_id)
                    was_stopped = check_stop(session_id)
                    mark_stream_done(session_id)
                    clear_stop(session_id)
                    if was_stopped:
                        try:
                            java_client.create_dialogue(
                                user_id=user_id, session_id=session_id,
                                conversation_text="（用户已主动停止生成）",
                                dialogue_type="AI", intent_type="stopped", plan_id=plan_id_int,
                            )
                        except Exception:
                            pass
                    _threadsafe_cb(_sentinel)  # 通知 async generator 结束

            threading.Thread(target=_run_graph, daemon=True).start()

            # 实时消费 queue：节点内部的 sse_callback 事件立即 yield
            try:
                while True:
                    item = await _queue.get()
                    if item is _sentinel:
                        break
                    if item is None:
                        # stopped 信号
                        yield f'data: {json.dumps({"type": "done", "stopped": True}, ensure_ascii=False)}\n\n'
                        break
                    yield item
            finally:
                # 客户端断开连接或发生异常时，主动触发停止信号，通知后台线程停止大模型调用
                request_stop(session_id)

    else:
        # ── 新建路径：构造 initial_state 从头执行 ──
        logger.info(f"[计划对话] 新建图执行 (session: {session_id})")

        placeholder_map = {}
        if breakdown_confirmed and parsed_breakdown and plan_id_int:
            modules = parsed_breakdown.get("modules", [])
            if modules:
                placeholder_map = _create_placeholder_resources(plan_id_int, modules)
                logger.info(f"[占位资源] 已创建 {len(placeholder_map)} 个占位记录")

        from app.utils.goal_utils import resolve_session_learning_goal
        _checkpoint_learning_goal = resolve_session_learning_goal(plan_id_int, session_id)
        try:
            existing_state = graph.get_state(config)
            if existing_state and existing_state.values:
                mem_goal = existing_state.values.get("learning_goal", "")
                if not _checkpoint_learning_goal and mem_goal and len(mem_goal) > 2 and mem_goal != message:
                    _checkpoint_learning_goal = mem_goal
            if _checkpoint_learning_goal:
                logger.info(f"[计划对话] 历史学习目标: {_checkpoint_learning_goal[:80]}")
        except Exception as e:
            logger.warning(f"[计划对话] 读取历史状态失败: {e}")

        initial_state: AgentState = {
            "user_id": user_id,
            "plan_id": plan_id_int,
            "task_id": chat_task_id,
            "session_id": session_id,
            "user_message": message,
            "human_feedback": human_feedback,
            "chat_history": chat_history,
            "user_profile": user_profile,
            "intent": "",
            "next_node": "",
            "needs_human_confirm": False,
            "profile_update_needed": False,
            "learning_goal": message,
            "_checkpoint_learning_goal": _checkpoint_learning_goal,
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
            "placeholder_resource_map": placeholder_map,
        }

        bg_state = {
            "events": [],
            "breakdown_confirmed": breakdown_confirmed,
            "ai_response_parts": [],
            "module_list": [],
            "orchestrated_content": None,
            "quiz_questions": None,
            "quiz_config": None,
            "generated_content": None,
            "new_breakdown": None,
            "generated_resource_info": [],
            "saved_module_orders": set(),
            "placeholder_map": placeholder_map,
        }

        async def event_stream() -> AsyncGenerator[str, None]:
            clear_stop(session_id)
            update_stream_text(session_id, "", "chat")
            _sentinel = object()
            _queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            # sse_callback 线程安全：从后台线程 put 到 async queue
            def _threadsafe_cb(data):
                loop.call_soon_threadsafe(_queue.put_nowait, data)

            # 注入 sse_callback（graph 节点内部调用）
            initial_state["sse_callback"] = _threadsafe_cb

            # 注入占位回调（graph 节点内部调用）
            def _create_placeholder_callback(modules: list) -> dict:
                if not plan_id_int or not modules:
                    return {}
                ph_map = _create_placeholder_resources(plan_id_int, modules)
                if ph_map:
                    bg_state["placeholder_map"] = ph_map
                    stream_registry.update_placeholder_map(session_id, ph_map)
                    _threadsafe_cb(
                        f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(ph_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n'
                    )
                    logger.info(f"[占位回调] 创建 {len(ph_map)} 个占位记录")
                return ph_map
            initial_state["create_placeholder_callback"] = _create_placeholder_callback

            # 注册 session 回调到全局注册表（绕过 checkpointer 序列化限制）
            stream_registry.register_session(
                session_id,
                sse_callback=_threadsafe_cb,
                create_placeholder_callback=_create_placeholder_callback,
                placeholder_resource_map=placeholder_map,
            )

            def _run_graph():
                """后台线程：执行 astream，将节点事件送入 queue"""
                try:
                    async def _do_run():
                        graph_inner = get_learning_graph()
                        logger.info(f"[对话流] 图执行开始")
                        async for event in graph_inner.astream(initial_state, config=config, stream_mode="updates"):
                            if check_stop(session_id):
                                _threadsafe_cb(None)  # stopped sentinel
                                return
                            for node_name, node_output in event.items():
                                if node_output is None or not isinstance(node_output, dict):
                                    continue
                                _update_bg_state_from_node(bg_state, node_output, node_name, plan_id_int, user_id, session_id, emit=_threadsafe_cb)
                                # module 事件已由 sse_callback 通过 resource_stream_text 实时推送，跳过避免重复
                                filtered_events = [e for e in node_output.get("stream_events", []) if e.get("event_type") != "module"]
                                filtered_output = {**node_output, "stream_events": filtered_events}
                                for sse_data in graph_step_to_sse(node_name, filtered_output):
                                    bg_state["ai_response_parts"] = _collect_stream_text(sse_data, bg_state["ai_response_parts"], session_id)
                                    _persist_profile_update(sse_data, user_id)
                                    _threadsafe_cb(sse_data)

                    asyncio.run(_do_run())
                    _bg_save_resources(bg_state, plan_id_int, user_id, session_id, message, chat_history, user_profile, chat_task_id, emit=_threadsafe_cb)
                    _save_plain_text_reply(bg_state["breakdown_confirmed"], bg_state["generated_resource_info"],
                                           bg_state["ai_response_parts"], user_id, session_id, plan_id_int)
                except Exception as e:
                    logger.error(f"[对话流] 线程异常: {e}", exc_info=True)
                    mark_stream_error(session_id, str(e))
                    _threadsafe_cb(f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n')
                finally:
                    stream_registry.unregister_session(session_id)
                    was_stopped = check_stop(session_id)
                    mark_stream_done(session_id)
                    clear_stop(session_id)
                    if was_stopped:
                        try:
                            java_client.create_dialogue(
                                user_id=user_id, session_id=session_id,
                                conversation_text="（用户已主动停止生成）",
                                dialogue_type="AI", intent_type="stopped", plan_id=plan_id_int,
                            )
                        except Exception:
                            pass
                    _threadsafe_cb(_sentinel)  # 通知 async generator 结束

            threading.Thread(target=_run_graph, daemon=True).start()

            # 实时消费 queue：节点内部的 sse_callback 事件立即 yield
            try:
                while True:
                    item = await _queue.get()
                    if item is _sentinel:
                        break
                    if item is None:
                        yield f'data: {json.dumps({"type": "done", "stopped": True}, ensure_ascii=False)}\n\n'
                        break
                    yield item
            finally:
                # 客户端断开连接或发生异常时，主动触发停止信号，通知后台线程停止大模型调用
                request_stop(session_id)

    def _bg_save_resources(bg_state, plan_id_int, user_id, session_id, message, chat_history, user_profile, chat_task_id, emit=None):
        """图执行完成后保存资源和记录"""
        bs = bg_state
        _emit = emit or bs["events"].append

        # 网络搜索资源：将 generated_content 转为 module_list
        if bs["generated_content"] and not bs["module_list"] and not bs["orchestrated_content"]:
            gc = bs["generated_content"]
            bs["module_list"] = [{
                "module_order": 1,
                "module_id": gc.get("module_id", 1),
                "title": gc.get("title", ""),
                "content": gc.get("content", ""),
                "module_type": _normalize_module_type(gc.get("content_type", "text")),
                "key_points": gc.get("key_points", []),
                "images": gc.get("images", []),
                "references": gc.get("references", []),
                "description": message,
            }]
            bs["orchestrated_content"] = {
                "title": gc.get("title", ""),
                "modules": bs["module_list"],
            }

        if bs["new_breakdown"] and plan_id_int and not bs["breakdown_confirmed"]:
            _save_breakdown_dialogue(user_id, session_id, plan_id_int, bs["new_breakdown"])

        if bs["breakdown_confirmed"] and plan_id_int:
            new_modules = [m for m in bs["module_list"]
                           if m.get("module_order") not in bs["saved_module_orders"]]
            if new_modules:
                new_ids = _save_modules_as_resources(plan_id_int, new_modules, bs["orchestrated_content"])
                for idx, rid in enumerate(new_ids):
                    mod = new_modules[idx] if idx < len(new_modules) else {}
                    bs["generated_resource_info"].append({
                        "id": rid,
                        "type": _normalize_module_type(mod.get("module_type", "text")),
                        "title": mod.get("title", f"模块 {idx + 1}"),
                    })
                    bs["saved_module_orders"].add(mod.get("module_order"))
                    # 为该资源创建已完成的 task 记录
                    try:
                        res_task = java_client.create_generation_task(
                            plan_id=plan_id_int, resource_id=rid, agent_chain="plan_chat",
                        )
                        if res_task and isinstance(res_task, dict):
                            java_client.update_generation_task(res_task["id"], 2, update_resource_status=False)
                    except Exception:
                        pass
                logger.info(f"[资源持久化] 保存 {len(new_modules)} 个新增模块")

        if not bs["breakdown_confirmed"] and bs["module_list"] and plan_id_int:
            new_modules = [m for m in bs["module_list"]
                           if m.get("module_order") not in bs["saved_module_orders"]]
            if new_modules:
                new_ids = _save_modules_as_resources(plan_id_int, new_modules, bs["orchestrated_content"])
                for idx, rid in enumerate(new_ids):
                    mod = new_modules[idx] if idx < len(new_modules) else {}
                    bs["generated_resource_info"].append({
                        "id": rid,
                        "type": _normalize_module_type(mod.get("module_type", "text")),
                        "title": mod.get("title", f"模块 {idx + 1}"),
                    })
                    bs["saved_module_orders"].add(mod.get("module_order"))
                    try:
                        res_task = java_client.create_generation_task(
                            plan_id=plan_id_int, resource_id=rid, agent_chain="plan_chat",
                        )
                        if res_task and isinstance(res_task, dict):
                            java_client.update_generation_task(res_task["id"], 2, update_resource_status=False)
                    except Exception:
                        pass
                logger.info(f"[资源持久化] 保存 {len(new_modules)} 个网络搜索资源")

        if bs["quiz_questions"] and plan_id_int:
            quiz_res_id = _save_quiz_resource(plan_id_int, bs["quiz_questions"], bs["quiz_config"])
            if quiz_res_id:
                bs["generated_resource_info"].append({
                    "id": quiz_res_id,
                    "type": "quiz",
                    "title": (bs["quiz_config"] or {}).get("title", "练习题"),
                })
                try:
                    res_task = java_client.create_generation_task(
                        plan_id=plan_id_int, resource_id=quiz_res_id, agent_chain="plan_chat",
                    )
                    if res_task and isinstance(res_task, dict):
                        java_client.update_generation_task(res_task["id"], 2, update_resource_status=False)
                except Exception:
                    pass

        if bs["generated_resource_info"] and plan_id_int:
            summary = _build_resource_summary(bs["module_list"], bs["quiz_questions"], bs["orchestrated_content"])
            dialogue_data = {
                "type": "resource_generated",
                "summary": summary,
                "resources": bs["generated_resource_info"],
            }
            try:
                result = java_client.create_dialogue(
                    user_id=user_id, session_id=session_id,
                    conversation_text=json.dumps(dialogue_data, ensure_ascii=False),
                    dialogue_type="AI", plan_id=plan_id_int, intent_type="resource_generated",
                )
                dialogue_id = result.get("data", {}).get("id") if isinstance(result, dict) else None
                if dialogue_id and bs["generated_resource_info"]:
                    min_resource_id = min(r["id"] for r in bs["generated_resource_info"] if r.get("id"))
                    try:
                        java_client.update_dialogue_resource_id(dialogue_id, min_resource_id)
                    except Exception as e:
                        logger.warning(f"[资源生成对话] 关联资源ID失败: {e}")
            except Exception as e:
                logger.warning(f"记录资源生成对话失败: {e}")

        # 更新生成任务状态
        if chat_task_id:
            try:
                java_client.update_generation_task(chat_task_id, 2 if not bs.get("error") else 3, update_resource_status=False)
            except Exception:
                pass

        # 画像维护 (放入后台线程执行，避免阻塞前端渲染卡片)
        if bs["generated_resource_info"] or bs.get("profile_update_needed"):
            threading.Thread(
                target=_async_profile_maintenance_sync, 
                args=(user_id, message, chat_history, user_profile),
                daemon=True
            ).start()

        # 会话压缩（后台线程）
        threading.Thread(target=lambda: asyncio.run(async_compress_and_save(
            user_id=user_id, session_id=session_id, plan_id=plan_id_int,
        )), daemon=True).start()

        # 最终事件
        if bs["generated_resource_info"]:
            _emit(
                f'data: {json.dumps({"type": "resource_generated", "resources": bs["generated_resource_info"]}, ensure_ascii=False)}\n\n'
            )
        _emit(
            f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
        )

    return StreamingResponse(
        event_stream(),
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
    type: str = Query("text", description="资源类型: text/mindmap/quiz/code/summary"),
    title: str = Query("", description="模块标题"),
    description: str = Query("", description="模块描述"),
    session_id: str = Query("", description="会话 ID（前端传入，为空时自动生成）"),
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
        # 确保 learning_behavior 字段完整
        if "learning_behavior" in user_profile:
            user_profile["learning_behavior"] = ensure_learning_behavior_fields(
                user_profile["learning_behavior"]
            )
    except Exception:
        pass

    # 获取该计划的对话历史作为上下文
    chat_history = []
    try:
        history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id_int, limit=20
        )
        for h in history:
            chat_history.append({
                "role": "user" if h.get("dialogueType") == "USER" else "assistant",
                "content": h.get("conversationText", ""),
            })
    except Exception:
        pass

    # 更新计划状态为"生成中"
    try:
        java_client.update_plan_status(plan_id_int, 1)
    except Exception:
        pass

    # 获取当前资源的 moduleOrder 和内容全文，补充资源使用相同编号
    current_module_order = 0
    source_resource_content = ""
    try:
        current_resource = java_client.get_resource_by_id(module_id_int)
        current_module_order, source_resource_content = _extract_source_resource_context(
            current_resource,
            fallback_title=title,
            fallback_description=description,
            plan_id=plan_id_int,
        )
        logger.info(f"[资源生成] 当前资源 moduleOrder={current_module_order}, 内容长度={len(source_resource_content)}")
    except Exception as e:
        logger.warning(f"[资源生成] 获取当前资源信息失败: {e}")

    # 构造以资源生成为目标的初始状态
    resource_message = f"请为以下模块生成{type}类型的学习资源: {title}"
    if description:
        resource_message += f"\n模块描述: {description}"

    # quiz 和 video 走独立流程，mindmap/summary/code 走类型资源生成，animation 走动画节点，其他走 RAG + 编排
    is_quiz = (type == "quiz")
    is_video = (type == "video")
    is_animation = (type == "animation")
    is_type_resource = type in ("mindmap", "summary", "code", "podcast")

    # 路由决策
    if is_quiz:
        intent = "generate_quiz"
        next_node = "quiz_generator"
    elif is_animation:
        intent = "generate_animation"
        next_node = NODE_ANIMATION_SKILL_GENERATOR
    elif is_type_resource:
        intent = "generate_type_resource"
        next_node = NODE_RESOURCE_TYPE_GENERATOR
    else:
        intent = "generate_resource"
        next_node = "rag_retriever"

    # 优先使用前端传入的 session_id，保持会话连续性
    effective_session_id = session_id if session_id else f"resource-{plan_id_int}-{module_id_int}"

    # 创建资源生成任务，用于关联 Token 消耗记录
    generation_task_id = None
    try:
        task_result = java_client.create_generation_task(
            plan_id=plan_id_int,
            resource_id=module_id_int,
            agent_chain=type,
        )
        generation_task_id = task_result.get("id") if isinstance(task_result, dict) else None
        if generation_task_id:
            logger.info(f"[资源生成] 已创建生成任务 task_id={generation_task_id}")
    except Exception as e:
        logger.warning(f"[资源生成] 创建生成任务失败: {e}")

    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id_int,
        "task_id": generation_task_id,
        "session_id": effective_session_id,
        "user_message": resource_message,
        "human_feedback": None,
        "chat_history": chat_history,
        "user_profile": user_profile,
        "intent": intent,
        "next_node": next_node,
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
        "max_iterations": 10,
        "accumulated_context": "",
        "source_resource_content": source_resource_content,
        "placeholder_resource_map": {1: {"id": module_id_int, "type": type, "title": title}},
    }

    session_id = effective_session_id

    # SSE 实时回调 + 业务状态追踪（复用与 /chat 一致的 bg_state 模式）
    bg_state = {
        "events": [],
        "breakdown_confirmed": False,
        "ai_response_parts": [],
        "module_list": [],
        "orchestrated_content": None,
        "quiz_questions": None,
        "quiz_config": None,
        "generated_content": None,
        "new_breakdown": None,
        "generated_resource_info": [],
        "saved_module_orders": set(),
        "placeholder_map": {},
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        clear_stop(session_id)
        try:
            # video 类型：使用自主视频搜索智能体，不走主流程 LangGraph
            if is_video:
                from app.agents.video_search_agent import search_videos_with_agent
                
                yield f'data: {json.dumps({"type": "progress", "content": f"正在启动智能体搜索「{title}」相关教学视频..."}, ensure_ascii=False)}\n\n'
                
                _v_sentinel = object()
                _v_queue: asyncio.Queue = asyncio.Queue()
                v_loop = asyncio.get_event_loop()
                
                def _v_sse_push(msg):
                    v_loop.call_soon_threadsafe(_v_queue.put_nowait, msg)
                    
                def _run_video_agent():
                    try:
                        videos = search_videos_with_agent(title, source_resource_content, _v_sse_push, user_id, generation_task_id)
                        _v_sse_push({"type": "result", "videos": videos})
                    except Exception as e:
                        logger.error(f"[视频生成] 智能体异常: {e}")
                        _v_sse_push({"type": "error", "error": str(e)})
                    finally:
                        _v_sse_push(_v_sentinel)
                        
                threading.Thread(target=_run_video_agent, daemon=True).start()
                
                videos = []
                while True:
                    item = await _v_queue.get()
                    if item is _v_sentinel:
                        break
                    if isinstance(item, str):
                        # 进度消息
                        yield item
                    elif isinstance(item, dict):
                        if item.get("type") == "result":
                            videos = item.get("videos", [])
                        elif item.get("type") == "error":
                            yield f'data: {json.dumps({"type": "error", "content": item.get("error")}, ensure_ascii=False)}\n\n'

                if videos:
                    res_id = _save_video_resource(plan_id_int, videos, current_module_order)
                    if res_id:
                        yield f'data: {json.dumps({"type": "resource_generated", "resources": [{"id": res_id, "type": "video", "title": f"{title} - 教学视频"}]}, ensure_ascii=False)}\n\n'
                else:
                    yield f'data: {json.dumps({"type": "progress", "content": "未找到相关教学视频，建议直接在视频平台搜索"}, ensure_ascii=False)}\n\n'
                yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
                
                if generation_task_id:
                    try:
                        java_client.update_generation_task(generation_task_id, 2, update_resource_status=False)
                    except Exception:
                        pass
                return

            # quiz 和其他类型走 LangGraph
            yield f'data: {json.dumps({"type": "progress", "content": "开始生成资源..."}, ensure_ascii=False)}\n\n'

            _sentinel = object()
            _queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            def _threadsafe_cb(data):
                loop.call_soon_threadsafe(_queue.put_nowait, data)

            initial_state["sse_callback"] = _threadsafe_cb

            # 提前推送占位记录，通知前端初始化对应的资源流式区域
            _threadsafe_cb(
                f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps([{"id": module_id_int, "type": type, "title": title}], ensure_ascii=False)}, ensure_ascii=False)}\n\n'
            )

            def _run_graph():
                """后台线程：执行 astream，将节点事件送入 queue"""
                try:
                    async def _do_run():
                        graph = get_learning_graph()
                        config = {"configurable": {"thread_id": session_id}}
                        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                            if check_stop(session_id):
                                _threadsafe_cb(None)
                                return
                            for node_name, node_output in event.items():
                                if node_output is None or not isinstance(node_output, dict):
                                    continue
                                _update_bg_state_from_node(bg_state, node_output, node_name, plan_id_int, user_id, session_id, emit=_threadsafe_cb)
                                # module 事件已由 sse_callback 通过 resource_stream_text 实时推送，跳过避免重复
                                filtered_events = [e for e in node_output.get("stream_events", []) if e.get("event_type") != "module"]
                                filtered_output = {**node_output, "stream_events": filtered_events}
                                for sse_data in graph_step_to_sse(node_name, filtered_output):
                                    bg_state["ai_response_parts"] = _collect_stream_text(sse_data, bg_state["ai_response_parts"], session_id)
                                    _persist_profile_update(sse_data, user_id)
                                    _threadsafe_cb(sse_data)

                    asyncio.run(_do_run())

                    # 从 bg_state 提取最终结果
                    orchestrated_content = bg_state["orchestrated_content"]
                    module_list = bg_state["module_list"]
                    quiz_questions = bg_state["quiz_questions"]
                    quiz_config = bg_state["quiz_config"]
                    generated_content = bg_state["generated_content"]
                    generated_resource_info = bg_state["generated_resource_info"]

                    # 网络搜索资源：将 generated_content 转为 module_list
                    if generated_content and not module_list and not orchestrated_content:
                        gc = generated_content
                        module_list = [{
                            "module_order": 1,
                            "module_id": gc.get("module_id", 1),
                            "title": gc.get("title", ""),
                            "content": gc.get("content", ""),
                            "module_type": _normalize_module_type(gc.get("module_type") or gc.get("content_type", "text")),
                            "key_points": gc.get("key_points", []),
                            "images": gc.get("images", []),
                            "references": gc.get("references", []),
                            "animationSpec": gc.get("animationSpec"),
                            "metadata": gc.get("metadata", {}),
                            "description": description,
                        }]
                        orchestrated_content = {
                            "title": gc.get("title", ""),
                            "modules": module_list,
                        }

                    # 图执行完成，保存资源
                    res_info = _persist_generated_resources(
                        plan_id_int, user_id, is_quiz, type, title, description,
                        module_list, orchestrated_content,
                        quiz_questions, quiz_config,
                        generated_content,
                        current_module_order, session_id,
                    )
                    if res_info:
                        bg_state["generated_resource_info"].extend(res_info)
                        _threadsafe_cb(f'data: {json.dumps({"type": "resource_generated", "resources": res_info}, ensure_ascii=False)}\n\n')
                    _threadsafe_cb(f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n')

                    if generation_task_id:
                        try:
                            java_client.update_generation_task(generation_task_id, 2, update_resource_status=False)
                        except Exception:
                            pass

                except Exception as e:
                    logger.error(f"[资源生成] 线程异常: {e}", exc_info=True)
                    _threadsafe_cb(f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n')
                    if not is_video:
                        _persist_generated_resources(
                            plan_id_int, user_id, is_quiz, type, title, description,
                            [], None, None, None, None,
                            current_module_order, session_id,
                        )
                    if generation_task_id:
                        try:
                            java_client.update_generation_task(generation_task_id, 3, update_resource_status=False)
                        except Exception:
                            pass
                finally:
                    _threadsafe_cb(_sentinel)

            threading.Thread(target=_run_graph, daemon=True).start()

            # 实时消费 queue
            _completed_normally = False
            try:
                while True:
                    item = await _queue.get()
                    if item is _sentinel:
                        _completed_normally = True
                        break
                    if item is None:
                        yield f'data: {json.dumps({"type": "done", "stopped": True}, ensure_ascii=False)}\n\n'
                        _completed_normally = True
                        break
                    yield item
            finally:
                # 仅在客户端断开连接或异常退出时触发停止信号，正常完成不触发
                if not _completed_normally:
                    request_stop(session_id)

        except Exception as e:
            logger.error(f"[资源生成] 异常: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/quiz/submit")
async def submit_quiz(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    resource_id: str = Query(..., description="测验资源 ID"),
    plan_id: str = Query(..., description="学习计划 ID"),
    answers: str = Query("{}", description="用户答案 JSON: {\"0\": \"A\", \"1\": [0,1], ...}"),
):
    """
    测验答题提交 - SSE 流式输出
    逐题批改，每题结果存入 quiz_record 表，通过 SSE 实时推送
    """
    try:
        ticket_info = java_client.validate_ticket(ticket)
        user_id = ticket_info["user_id"]
    except Exception as e:
        logger.error(f"Ticket 验证失败: {e}")
        return StreamingResponse(
            _error_stream(f"认证失败: {str(e)}"),
            media_type="text/event-stream",
        )

    resource_id_int = int(resource_id) if resource_id and resource_id.isdigit() else 0
    plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else 0

    try:
        user_answers = json.loads(answers)
    except Exception:
        user_answers = {}

    # 获取 quiz 资源数据
    try:
        resource = java_client.get_resource_by_id(resource_id_int)
    except Exception as e:
        return StreamingResponse(
            _error_stream(f"获取资源失败: {str(e)}"),
            media_type="text/event-stream",
        )

    # 解析题目列表
    module_data = resource.get("moduleData", {})
    if isinstance(module_data, str):
        try:
            module_data = json.loads(module_data)
        except Exception:
            module_data = {}

    raw_questions = module_data.get("questions", [])
    if not raw_questions:
        return StreamingResponse(
            _error_stream("题目数据为空"),
            media_type="text/event-stream",
        )

    logger.info(f"[测验批改] 用户 {user_id}, 资源 {resource_id_int}, 共 {len(raw_questions)} 题")

    async def stream():
        from app.agents.llm_factory import get_quiz_grader_llm

        total = len(raw_questions)
        correct_count = 0
        score_sum = 0.0
        details = [None] * total  # 预分配，按索引填充

        # ---------- 1. 预处理所有题目数据 ----------
        prepared = []
        for i, q in enumerate(raw_questions):
            question_text = q.get("question_text", q.get("question", ""))
            question_type = q.get("question_type", q.get("type", "short_answer"))
            correct_answer = q.get("correct_answer", q.get("correctAnswer", ""))
            explanation = q.get("explanation", "")
            difficulty = q.get("difficulty", 3)

            raw_ans = user_answers.get(str(i), user_answers.get(i, None))
            if raw_ans is None:
                user_answer_text = "未作答"
            elif isinstance(raw_ans, list):
                options = q.get("options", [])
                if options and all(isinstance(a, int) for a in raw_ans):
                    user_answer_text = ", ".join(options[a] for a in raw_ans if 0 <= a < len(options))
                else:
                    user_answer_text = ", ".join(str(a) for a in raw_ans)
            elif isinstance(raw_ans, int) and q.get("options"):
                opts = q.get("options", [])
                user_answer_text = opts[raw_ans] if 0 <= raw_ans < len(opts) else str(raw_ans)
            else:
                user_answer_text = str(raw_ans)

            prepared.append({
                "index": i,
                "question_text": question_text,
                "question_type": question_type,
                "correct_answer": json.dumps(correct_answer, ensure_ascii=False) if isinstance(correct_answer, list) else str(correct_answer),
                "explanation": explanation,
                "difficulty": difficulty,
                "user_answer_text": user_answer_text,
            })

        # ---------- 2. 并行批改 + 每题流式推送 ----------
        event_queue: asyncio.Queue = asyncio.Queue()

        # 初始推送开始信号到队列
        event_queue.put_nowait({"type": "grading_started", "total": total})

        async def grade_one(idx: int, prep: dict, llm):
            """单题批改协程：流式收集 token，完成后存 DB 并推送结果"""
            def on_token(token: str):
                """LLM 每输出一个 token，通过 queue 推送给 SSE"""
                try:
                    event_queue.put_nowait({
                        "type": "grading_token",
                        "index": idx,
                        "token": token,
                    })
                except Exception:
                    pass

            messages = [
                {"role": "system", "content": QUIZ_GRADER_PROMPT},
                {"role": "user", "content": f"题目: {prep['question_text']}\n题型: {prep['question_type']}\n参考答案: {prep['correct_answer']}\n答案解析: {prep['explanation']}\n\n用户回答: {prep['user_answer_text']}\n\n请批改并输出 JSON:"},
            ]

            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: llm.chat_json_stream(messages, on_chunk=on_token, max_tokens=2048)
                )
                record_from_mimo(llm, user_id, "quiz_grading_inline", generation_task_id)
            except Exception as e:
                logger.error(f"[测验批改] Q{idx + 1} LLM 批改异常: {e}")
                result = {"score": 0, "is_correct": False, "feedback": f"批改异常: {str(e)}",
                          "key_points_hit": [], "key_points_missed": [], "improvement_suggestions": []}

            # 保存到 quiz_record 表
            try:
                java_client.create_quiz_record(
                    resource_id=resource_id_int,
                    user_id=user_id,
                    plan_id=plan_id_int,
                    question_type=prep["question_type"],
                    question_text=prep["question_text"],
                    correct_answer=prep["correct_answer"],
                    user_answer=prep["user_answer_text"],
                    score=result.get("score", 0),
                    is_correct=1 if result.get("is_correct", False) else 0,
                    feedback=result.get("feedback", ""),
                    difficulty=prep["difficulty"],
                )
            except Exception as e:
                logger.warning(f"[测验批改] Q{idx + 1} 保存答题记录失败: {e}")

            detail = {
                "index": idx,
                "question": prep["question_text"],
                "question_type": prep["question_type"],
                "user_answer": prep["user_answer_text"],
                "correct_answer": prep["correct_answer"],
                "score": result.get("score", 0),
                "is_correct": result.get("is_correct", False),
                "feedback": result.get("feedback", ""),
                "key_points_hit": result.get("key_points_hit", []),
                "key_points_missed": result.get("key_points_missed", []),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "explanation": prep["explanation"],
            }

            # 推送该题最终结果
            event_queue.put_nowait({
                "type": "quiz_question_result",
                "index": idx,
                "result": detail,
            })
            return idx, detail

        async def run_grading_and_persistence():
            nonlocal correct_count, score_sum
            try:
                tasks = []
                for idx, prep in enumerate(prepared):
                    llm = get_quiz_grader_llm()
                    tasks.append(asyncio.create_task(grade_one(idx, prep, llm)))

                completed = 0
                for coro in asyncio.as_completed(tasks):
                    idx, detail = await coro
                    completed += 1
                    details[idx] = detail
                    if detail.get("is_correct"):
                        correct_count += 1
                    score_sum += detail.get("score", 0)
                    logger.info(f"[测验批改] Q{idx + 1} 完成 ({completed}/{total})")

                # 总体结果（基于每题 score 加权平均）
                overall_score = round(score_sum / total * 100) if total > 0 else 0
                summary = {
                    "score": overall_score,
                    "total": total,
                    "correct": correct_count,
                    "details": [d for d in details if d is not None],
                }
                event_queue.put_nowait({
                    "type": "quiz_result",
                    "result": summary
                })

                # 将批改结果写入资源的 module_data，下次打开时可直接显示
                try:
                    updated_module_data = dict(module_data)
                    updated_module_data["latestResult"] = {
                        "answers": user_answers,
                        "score": overall_score,
                        "total": total,
                        "correct": correct_count,
                        "details": summary["details"],
                        "submittedAt": datetime.now().isoformat(),
                    }
                    java_client.update_resource_content(resource_id_int, json.dumps(updated_module_data, ensure_ascii=False))
                    logger.info(f"[测验批改] 已将批改结果写入资源 {resource_id_int} 的 module_data")
                except Exception as e:
                    logger.warning(f"[测验批改] 写入 module_data 失败: {e}")

                # 后台画像维护
                threading.Thread(target=_async_profile_maintenance_sync, kwargs={
                    "user_id": user_id,
                    "user_message": f"完成测验，得分 {overall_score}",
                    "chat_history": [],
                    "user_profile": {},
                    "quiz_result": summary,
                }, daemon=True).start()

                event_queue.put_nowait({"type": "done"})

            except Exception as e:
                logger.error(f"[测验批改] 后台批改任务异常: {e}", exc_info=True)
                event_queue.put_nowait({"type": "error", "content": str(e)})
            finally:
                event_queue.put_nowait(None)

        # 启动后台批改与持久化任务（生命周期独立于 stream 协程的取消）
        asyncio.create_task(run_grading_and_persistence())

        # ---------- 3. 从 queue 消费事件，yield 给 SSE ----------
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
        except GeneratorExit:
            logger.warning(f"[测验批改] 客户端断开连接，批改与持久化任务将在后台继续执行")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tutor/chat")
async def tutor_chat(
    ticket: str = Query(..., description="Java 后端签发的短期 Ticket"),
    plan_id: str = Query(..., description="学习计划 ID"),
    resource_id: str = Query(..., description="当前模块资源 ID"),
    message: str = Query(..., description="用户消息"),
    session_id: str = Query("", description="会话 ID"),
):
    """
    智能辅导对话 - SSE 流式输出
    针对用户当前点击的模块内容进行个性化辅导
    """
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
    resource_id_int = int(resource_id) if resource_id and resource_id.isdigit() else 0

    if not session_id:
        session_id = f"tutor-{plan_id}-{user_id}"

    logger.info(f"[智能辅导] 用户 {user_id}, 计划 {plan_id_int}, 资源 {resource_id_int}, 会话 {session_id}")

    # 记录用户消息
    try:
        java_client.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            conversation_text=message,
            dialogue_type="USER",
            plan_id=plan_id_int,
            intent_type="chat",
        )
    except Exception as e:
        logger.warning(f"[智能辅导] 记录用户消息失败: {e}")

    # 事件队列（tutor_agent 通过 sse_callback 推入）
    _sse_events = []
    def _sse_callback(data):
        _sse_events.append(data)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            from app.agents.tutor_agent import tutor_chat as _tutor_chat

            # 在线程池中执行辅导智能体（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            def _run_and_save():
                res = asyncio.run(_tutor_chat(
                    user_id=user_id,
                    plan_id=plan_id_int,
                    session_id=session_id,
                    resource_id=resource_id_int,
                    user_message=message,
                    sse_callback=_sse_callback,
                ))
                if res:
                    try:
                        java_client.create_dialogue(
                            user_id=user_id,
                            session_id=session_id,
                            conversation_text=res,
                            dialogue_type="AI",
                            plan_id=plan_id_int,
                            intent_type="chat",
                        )
                    except Exception as e:
                        logger.warning(f"[智能辅导] 记录 AI 回复失败: {e}")
                return res

            task = loop.run_in_executor(
                None,
                _run_and_save
            )

            # 实时轮询推送事件（真流式）
            while not task.done():
                while _sse_events:
                    yield _sse_events.pop(0)
                await asyncio.sleep(0.05)

            # 推送执行期间产生的残余事件
            while _sse_events:
                yield _sse_events.pop(0)

            # 后台会话压缩
            asyncio.create_task(async_compress_and_save(
                user_id=user_id, session_id=session_id, plan_id=plan_id_int,
            ))

        except Exception as e:
            logger.error(f"[智能辅导] 执行异常: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _letter_to_index(letter: str) -> int:
    """字母转0-based索引: A->0, B->1, ..., E->4"""
    return ord(letter.upper()) - ord('A')


def _check_answer(user_answer, correct_answer: str, question_type: str, options: list) -> bool:
    """比对选择/判断题答案"""
    if user_answer is None:
        return False

    if question_type == "single_choice":
        # user_answer 可能是索引(int)或文本(str)
        if isinstance(user_answer, int):
            correct_text = correct_answer.strip()
            # correctAnswer 可能是 "A" 格式或选项文本
            if len(correct_text) == 1 and correct_text.upper() in "ABCDE":
                return _letter_to_index(correct_text) == user_answer
            # 或者是选项文本
            return options[user_answer].strip() == correct_text if 0 <= user_answer < len(options) else False
        return str(user_answer).strip().lower() == str(correct_answer).strip().lower()

    elif question_type == "multiple_choice":
        if isinstance(user_answer, list) and options:
            # 索引列表 -> 排序后比对
            selected = sorted(user_answer)
            # correctAnswer 可能是 "A,C" 格式、JSON数组 '["A","C"]'、或选项文本列表
            ca = str(correct_answer).strip()
            # 处理 Python 列表表示 "['A', 'C']"
            if ca.startswith("[") and ca.endswith("]"):
                try:
                    import json as _json
                    arr = _json.loads(ca.replace("'", '"'))
                    if isinstance(arr, list):
                        if all(isinstance(x, int) for x in arr):
                            return selected == sorted(arr)
                        indices = sorted(_letter_to_index(x) if isinstance(x, str) and len(x) == 1 and x.upper() in "ABCDE" else int(x) if str(x).isdigit() else -1 for x in arr)
                        indices = [i for i in indices if i >= 0]
                        return selected == indices
                except Exception:
                    pass
            # 字母逗号分隔 "A,C"
            parts = [p.strip() for p in ca.replace("，", ",").split(",") if p.strip()]
            if all(len(p) == 1 and p.upper() in "ABCDE" for p in parts):
                correct_indices = sorted(_letter_to_index(p) for p in parts)
                return selected == correct_indices
            # 选项文本比对
            selected_texts = sorted(options[i].strip() for i in selected if 0 <= i < len(options))
            correct_texts = sorted(t.strip() for t in parts)
            return selected_texts == correct_texts
        return False

    elif question_type == "true_false":
        ua = str(user_answer).strip()
        ca = str(correct_answer).strip()
        # 标准化
        norm = {"正确": "true", "对": "true", "是": "true", "true": "true", "t": "true", "1": "true",
                 "错误": "false", "错": "false", "否": "false", "false": "false", "f": "false", "0": "false"}
        return norm.get(ua.lower(), ua.lower()) == norm.get(ca.lower(), ca.lower())

    return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


def _display_answer(correct_answer: str, question_type: str) -> str:
    """将内部答案格式转为用户可读的显示文本"""
    if question_type == "true_false":
        ca = str(correct_answer).strip().lower()
        if ca in ("a", "正确", "对", "是", "true", "t", "1"):
            return "正确"
        if ca in ("b", "错误", "错", "否", "false", "f", "0"):
            return "错误"
        return str(correct_answer)
    if question_type == "single_choice":
        # "A" -> "A"，已经是可读的
        return str(correct_answer)
    return str(correct_answer)


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    yield f'data: {json.dumps({"type": "error", "content": message}, ensure_ascii=False)}\n\n'


def _extract_source_resource_context(
    resource: dict,
    fallback_title: str = "",
    fallback_description: str = "",
    plan_id: int = 0,
) -> tuple[int, str]:
    """提取补充资源生成所需的源资源内容。

    优先级：当前资源正文 → 同模块兄弟资源正文 → 标题+描述兜底。
    """
    current_module_order = 0
    source_resource_content = ""
    current_resource_id = 0

    if isinstance(resource, dict):
        current_module_order = resource.get("moduleOrder", 0) or 0
        current_resource_id = resource.get("id", 0) or 0
        md = resource.get("moduleData")
        if isinstance(md, str):
            try:
                md = json.loads(md)
            except Exception:
                md = {}
        if isinstance(md, dict):
            source_resource_content = (
                md.get("content")
                or md.get("html")
            )

    # 正文为空时，尝试从同模块兄弟资源获取正文
    if not source_resource_content and plan_id and current_module_order:
        try:
            siblings = java_client.get_resources_by_module(plan_id, current_module_order)
            preferred_types = ("text", "document", "reading", "summary", "code")
            for preferred in preferred_types:
                for sibling in (siblings or []):
                    if sibling.get("id") == current_resource_id:
                        continue
                    if sibling.get("status") != 2 or sibling.get("moduleType") != preferred:
                        continue
                    smd = sibling.get("moduleData")
                    if isinstance(smd, str):
                        try:
                            smd = json.loads(smd)
                        except Exception:
                            smd = {}
                    if isinstance(smd, dict):
                        content = smd.get("content") or smd.get("summary") or ""
                        if content:
                            source_resource_content = content
                            logger.info(
                                "[资源生成] 动画源内容来自同模块 %s 资源: id=%s, 长度=%d",
                                preferred, sibling.get("id"), len(content),
                            )
                            break
                if source_resource_content:
                    break
        except Exception as e:
            logger.warning("[资源生成] 查找同模块兄弟资源失败: %s", e)

    # 最终兜底：标题+描述
    if not source_resource_content:
        md = resource.get("moduleData") if isinstance(resource, dict) else {}
        if isinstance(md, str):
            try:
                md = json.loads(md)
            except Exception:
                md = {}
        if isinstance(md, dict):
            source_resource_content = "\n\n".join(
                part for part in [
                    md.get("module_title") or md.get("title") or fallback_title,
                    md.get("module_description") or md.get("description") or fallback_description,
                ]
                if part
            )
        if not source_resource_content:
            source_resource_content = "\n\n".join(
                part for part in [fallback_title, fallback_description] if part
            )
        if source_resource_content:
            logger.warning(
                "[资源生成] 未找到正文资源，使用标题/描述兜底 (plan=%s, module=%s, 长度=%d)",
                plan_id, current_module_order, len(source_resource_content),
            )

    return current_module_order, source_resource_content


def _build_resource_summary(module_list: list, quiz_questions: list = None, orchestrated_content: dict = None) -> str:
    """构建生成资源的简要摘要"""
    parts = []
    if module_list:
        titles = [m.get("title", "") for m in module_list if m.get("title")]
        raw_types = list({_normalize_module_type(m.get("module_type", "text")) for m in module_list})
        type_map = {
            "text": "图文",
            "video": "视频",
            "animation": "动画",
            "podcast": "播客",
            "code": "代码交互",
            "mindmap": "思维导图",
            "quiz": "测试练习"
        }
        translated_types = [type_map.get(t, t) for t in raw_types]
        type_label = "/".join(translated_types)
        parts.append(f"已生成 {len(module_list)} 个「{type_label}」学习模块：{'、'.join(titles)}")
    if quiz_questions:
        parts.append(f"已生成 {len(quiz_questions)} 道练习题")
    if orchestrated_content and orchestrated_content.get("summary"):
        parts.append(orchestrated_content["summary"])
    return "；".join(parts) if parts else "学习资源生成完成"


def _persist_generated_resources(
    plan_id_int: int,
    user_id: int,
    is_quiz: bool,
    resource_type: str,
    title: str,
    description: str,
    module_list: list,
    orchestrated_content: dict,
    quiz_questions: list,
    quiz_config: dict,
    generated_content: dict = None,
    current_module_order: int = 0,
    session_id: str = "",
) -> list:
    """将生成的资源持久化到数据库（与 SSE 解耦，确保断开连接时也能保存）"""
    generated_resource_info = []

    # 类型资源（mindmap/summary/code/animation）：直接从 generated_content 保存
    is_direct_generated_resource = resource_type in ("mindmap", "summary", "code", "animation")
    if is_direct_generated_resource and generated_content and plan_id_int:
        module_data = {
            "title": generated_content.get("title", title),
            "description": generated_content.get("description", description),
            "content": generated_content.get("content", ""),
            "module_title": generated_content.get("title", title),
            "references": generated_content.get("references", []),
        }
        if resource_type == "animation":
            module_data["html"] = generated_content.get("html", generated_content.get("content", ""))
            module_data["animationSpec"] = generated_content.get("animationSpec", {})
            module_data["duration"] = generated_content.get("duration")
            module_data["metadata"] = generated_content.get("metadata", {})
        try:
            result = java_client.create_resource(
                plan_id=plan_id_int,
                module_type=resource_type,
                module_data=json.dumps(module_data, ensure_ascii=False),
                module_order=current_module_order,
                status=2,
                generated_by_agent="animation_skill_generator" if resource_type == "animation" else "resource_type_generator",
            )
            new_resource_id = result.get("id") if isinstance(result, dict) else 0
            if new_resource_id:
                generated_resource_info.append({
                    "id": new_resource_id,
                    "type": resource_type,
                    "title": module_data.get("title", title),
                })
                logger.info(f"[资源持久化] 已创建{resource_type}补充资源，ID={new_resource_id}，moduleOrder={current_module_order}")
        except Exception as e:
            logger.warning(f"[资源持久化] 创建{resource_type}补充资源失败: {e}")

    elif is_quiz:
        if quiz_questions and plan_id_int:
            quiz_res_id = _save_quiz_resource(plan_id_int, quiz_questions, quiz_config, module_order=current_module_order)
            if quiz_res_id:
                generated_resource_info.append({
                    "id": quiz_res_id,
                    "type": "quiz",
                    "title": (quiz_config or {}).get("title", title),
                })
    else:
        if (orchestrated_content or module_list) and plan_id_int:
            module_data = {}
            if orchestrated_content:
                module_data["title"] = orchestrated_content.get("title", title)
                module_data["description"] = orchestrated_content.get("description", description)
                module_data["summary"] = orchestrated_content.get("summary", "")
                module_data["modules"] = orchestrated_content.get("modules", [])
                if "references" in orchestrated_content:
                    module_data["references"] = orchestrated_content["references"]
            if module_list:
                module_data["content"] = module_list[0].get("content", "") if module_list else ""
                if not module_data.get("title"):
                    module_data["title"] = module_list[0].get("title", title)
                # 传递图片数据
                images = module_list[0].get("images", [])
                if images:
                    module_data["images"] = images
                # 传递参考文献数据
                references = module_list[0].get("references", [])
                if references:
                    module_data["references"] = references
            if not module_data.get("title"):
                module_data["title"] = title
            try:
                result = java_client.create_resource(
                    plan_id=plan_id_int,
                    module_type=resource_type,
                    module_data=json.dumps(module_data, ensure_ascii=False),
                    module_order=current_module_order,
                    status=2,
                    generated_by_agent="content_orchestrator",
                )
                new_resource_id = result.get("id") if isinstance(result, dict) else 0
                if new_resource_id:
                    generated_resource_info.append({
                        "id": new_resource_id,
                        "type": resource_type,
                        "title": module_data.get("title", title),
                    })
                    logger.info(f"[资源持久化] 已创建{resource_type}补充资源，ID={new_resource_id}，moduleOrder={current_module_order}")
            except Exception as e:
                logger.warning(f"[资源持久化] 创建{resource_type}补充资源失败: {e}")

    # 保存对话记录
    if generated_resource_info and plan_id_int:
        summary = _build_resource_summary(module_list, quiz_questions, orchestrated_content)
        dialogue_data = {
            "type": "resource_generated",
            "summary": summary,
            "resources": generated_resource_info,
        }
        try:
            java_client.create_dialogue(
                user_id=user_id,
                session_id=session_id,
                conversation_text=json.dumps(dialogue_data, ensure_ascii=False),
                dialogue_type="AI",
                plan_id=plan_id_int,
                intent_type="resource_generated",
            )
        except Exception as e:
            logger.warning(f"记录资源生成对话失败: {e}")

    return generated_resource_info


def _search_videos(module_title: str) -> list:
    """搜索与模块相关的教学视频"""
    try:
        from app.agents.search_utils import search_tavily
    except ImportError:
        logger.warning("[视频搜索] 无法导入 search_tavily")
        return []

    # 中英文双语搜索
    results_cn, _ = search_tavily(f"{module_title} 教学视频", max_results=5, validate_images=False)
    results_en, _ = search_tavily(f"{module_title} tutorial video", max_results=3, validate_images=False)

    # 视频平台白名单
    video_domains = [
        "youtube.com", "youtu.be", "bilibili.com", "b23.tv",
        "v.qq.com", "iqiyi.com", "youku.com", "vimeo.com",
        "ted.com", "coursera.org", "edx.org", "mooc.cn",
    ]

    seen_urls = set()
    videos = []
    for r in results_cn + results_en:
        url = r.get("url", "")
        if not url or url in seen_urls:
            continue
        # 检查是否为视频平台
        domain_match = any(d in url.lower() for d in video_domains)
        # 也接受标题中含"视频"/"video"的结果
        title_match = any(k in r.get("title", "").lower() for k in ["视频", "video", "教程", "tutorial", "讲座", "课程"])
        if domain_match or title_match:
            seen_urls.add(url)
            # 识别平台
            platform = "其他"
            if "youtube.com" in url or "youtu.be" in url:
                platform = "YouTube"
            elif "bilibili.com" in url or "b23.tv" in url:
                platform = "Bilibili"
            elif "v.qq.com" in url:
                platform = "腾讯视频"
            elif "iqiyi.com" in url:
                platform = "爱奇艺"
            elif "youku.com" in url:
                platform = "优酷"
            elif "vimeo.com" in url:
                platform = "Vimeo"
            elif "ted.com" in url:
                platform = "TED"
            elif "coursera.org" in url:
                platform = "Coursera"
            elif "edx.org" in url:
                platform = "edX"
            videos.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": r.get("snippet", ""),
                "platform": platform,
            })

    logger.info(f"[视频搜索] '{module_title}' -> 找到 {len(videos)} 个视频")
    return videos


def _save_video_resource(plan_id: int, videos: list, module_order: int = None) -> int:
    """将视频搜索结果保存为 video 类型的学习资源"""
    try:
        if not videos:
            return 0
        module_data = {
            "title": "教学视频",
            "description": "相关教学视频资源",
            "videos": videos,
        }
        if module_order is None:
            existing = java_client.get_plan_resources(plan_id)
            module_order = max((r.get("moduleOrder", 0) for r in existing), default=0) + 1
        result = java_client.create_resource(
            plan_id=plan_id,
            module_type="video",
            module_data=json.dumps(module_data, ensure_ascii=False),
            module_order=module_order,
            status=2,
            generated_by_agent="video_search",
        )
        resource_id = result.get("id") if isinstance(result, dict) else 0
        logger.info(f"[资源持久化] 已保存视频资源到计划 {plan_id}，共 {len(videos)} 个视频，ID={resource_id}")
        return resource_id
    except Exception as e:
        logger.warning(f"[资源持久化] 保存视频资源失败: {e}")
        return 0


def _save_plain_text_reply(breakdown_confirmed, generated_resource_info,
                           ai_response_parts, user_id, session_id, plan_id_int):
    """未生成资源时，保存纯文本 AI 回复"""
    if not breakdown_confirmed and not generated_resource_info:
        ai_response = "\n".join(ai_response_parts) if ai_response_parts else "处理完成"
        if ai_response and ai_response != "处理完成":
            try:
                java_client.create_dialogue(
                    user_id=user_id,
                    session_id=session_id,
                    conversation_text=ai_response,
                    dialogue_type="AI",
                    plan_id=plan_id_int,
                    intent_type="plan_chat",
                )
            except Exception as e:
                logger.warning(f"记录 AI 回复失败: {e}")


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
        reason = dimensions.get("reason", "对话分析自动更新")
        logger.info(f"[画像持久化] 保存用户 {user_id} 的画像更新: {reason}")
        java_client.save_user_profile(user_id, updated_behavior, reason)
        logger.info(f"[画像持久化] 画像保存成功")
    except Exception as e:
        logger.warning(f"[画像持久化] 保存失败: {e}")


def _async_profile_maintenance_sync(
    user_id: int,
    user_message: str,
    chat_history: list,
    user_profile: dict,
    quiz_result: dict = None,
):
    """同步执行画像维护（在线程中调用，不阻塞事件循环）"""
    try:
        logger.info(f"[画像维护] 开始更新用户 {user_id} 的画像")
        state = {
            "user_message": user_message,
            "chat_history": chat_history,
            "user_profile": user_profile,
            "quiz_result": quiz_result,
        }
        result = profile_maintainer_node(state)
        if result.get("stream_events"):
            for event in result["stream_events"]:
                if event.get("event_type") == "profile_update":
                    updated_behavior = event.get("data", {}).get("updated_behavior", {})
                    reason = event.get("data", {}).get("reason", "后台自动更新")
                    confidence = event.get("data", {}).get("confidence", 0)
                    if updated_behavior:
                        java_client.save_user_profile(user_id, updated_behavior, reason)
                        logger.info(f"[画像维护] 用户 {user_id} 画像更新成功 (置信度: {confidence:.2f})")
        else:
            logger.info(f"[画像维护] 用户 {user_id} 无需更新画像")
    except Exception as e:
        logger.error(f"[画像维护] 更新失败: {str(e)}", exc_info=True)


VALID_MODULE_TYPES = {"text", "image", "diagram", "code", "summary", "mindmap", "animation"}


def _normalize_module_type(module_type) -> str:
    """将 LLM 输出的 module_type 归一化为前端支持的类型"""
    if not isinstance(module_type, str) or not module_type:
        return "text"
    mt = module_type.strip().lower()
    return mt if mt in VALID_MODULE_TYPES else "text"


def _soft_delete_breakdown_dialogue(user_id: int, session_id: str, plan_id: int):
    """软删除该会话中之前的 task_breakdown 对话记录"""
    try:
        history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id, session_id=session_id, limit=50
        )
        for h in history:
            if h.get("intentType") == "task_breakdown" and h.get("dialogueType") == "AI":
                dialogue_id = h.get("id")
                if dialogue_id:
                    java_client.delete_dialogue(dialogue_id)
                    logger.info(f"[任务分解] 已软删除旧的分解记录 id={dialogue_id}")
    except Exception as e:
        logger.warning(f"[任务分解] 软删除旧分解记录失败: {e}")


def _save_breakdown_dialogue(user_id: int, session_id: str, plan_id: int, breakdown: dict, resource_ids: list = None):
    """将任务分解保存为对话记录（intent_type=task_breakdown），并关联资源ID"""
    try:
        modules = breakdown.get("modules", [])
        text = json.dumps(breakdown, ensure_ascii=False)
        result = java_client.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            conversation_text=text,
            dialogue_type="AI",
            plan_id=plan_id,
            intent_type="task_breakdown",
        )
        dialogue_id = result.get("data", {}).get("id") if isinstance(result, dict) else None
        # 关联第一个资源ID（主资源）
        if dialogue_id and resource_ids:
            try:
                java_client.update_dialogue_resource_id(dialogue_id, resource_ids[0])
            except Exception as e:
                logger.warning(f"[任务分解持久化] 关联资源ID失败: {e}")
        logger.info(f"[任务分解持久化] 已保存任务分解，{len(modules)} 个模块")
    except Exception as e:
        logger.warning(f"[任务分解持久化] 保存失败: {e}")


def _save_quiz_resource(plan_id: int, questions: list, quiz_config: dict = None, module_order: int = None) -> int:
    """将生成的题目保存为 quiz 类型的学习资源，返回资源 ID"""
    try:
        if not questions:
            return 0
        config = quiz_config or {}
        module_data = {
            "title": config.get("title", "练习题"),
            "description": config.get("description", ""),
            "questions": [
                {
                    "index": i,
                    "type": q.get("question_type", "short_answer"),
                    "question": q.get("question_text", ""),
                    "options": q.get("options"),
                    "correctAnswer": q.get("correct_answer", ""),
                    "explanation": q.get("explanation", ""),
                    "difficulty": q.get("difficulty", 3),
                    "points": 1,
                }
                for i, q in enumerate(questions)
            ],
            "totalPoints": len(questions),
            "estimatedMinutes": len(questions) * 2,
        }
        # 使用指定的 moduleOrder（与所属模块一致），否则取最大值 +1
        if module_order is None:
            existing = java_client.get_plan_resources(plan_id)
            module_order = max((r.get("moduleOrder", 0) for r in existing), default=0) + 1
        result = java_client.create_resource(
            plan_id=plan_id,
            module_type="quiz",
            module_data=json.dumps(module_data, ensure_ascii=False),
            module_order=module_order,
            status=2,
            generated_by_agent="quiz_generator",
        )
        resource_id = result.get("id") if isinstance(result, dict) else 0
        logger.info(f"[资源持久化] 已保存题目资源到计划 {plan_id}，共 {len(questions)} 题，ID={resource_id}，moduleOrder={module_order}")
        return resource_id
    except Exception as e:
        logger.warning(f"[资源持久化] 保存题目资源失败: {e}")
        return 0


def _create_placeholder_resources(plan_id: int, modules: list) -> dict:
    """在 learning_resource 表中创建占位记录，返回 {module_order: {id, type, title}} 映射"""
    placeholder_map = {}
    try:
        existing = java_client.get_plan_resources(plan_id)
        max_order = max((r.get("moduleOrder", 0) for r in existing), default=0)

        for i, mod in enumerate(modules):
            module_order = mod.get("module_order", i + 1)
            module_type = "text"
            resources = mod.get("resources", [])
            if resources:
                module_type = _normalize_module_type(resources[0].get("resource_type", "text"))
            title = mod.get("title", f"模块 {module_order}")
            module_data = {
                "title": title,
                "description": mod.get("description", ""),
            }
            try:
                result = java_client.create_resource(
                    plan_id=plan_id,
                    module_type=module_type,
                    module_data=json.dumps(module_data, ensure_ascii=False),
                    module_order=max_order + module_order,
                    status=1,  # 生成中
                    generated_by_agent="content_orchestrator",
                )
                res_id = result.get("id") if isinstance(result, dict) else 0
                if res_id:
                    placeholder_map[module_order] = {
                        "id": res_id,
                        "type": module_type,
                        "title": title,
                    }
                    # 立即创建 task 记录（resource_id=真实资源ID），确保后端崩溃后前端能检测到卡死
                    try:
                        java_client.create_generation_task(
                            plan_id=plan_id, resource_id=res_id, agent_chain="plan_chat",
                        )
                    except Exception as e:
                        logger.warning(f"[占位资源] 创建 task 记录失败: {e}")
                    logger.info(f"[占位资源] 创建模块 {module_order} 占位记录，ID={res_id}")
            except Exception as e:
                logger.warning(f"[占位资源] 创建模块 {module_order} 占位记录失败: {e}")
    except Exception as e:
        logger.warning(f"[占位资源] 创建占位记录异常: {e}")
    return placeholder_map


def _save_modules_as_resources(plan_id: int, module_list: list, orchestrated_content: dict = None) -> list:
    """将确认后的学习模块保存为 learning_resource 记录，返回创建的资源ID列表"""
    try:
        if not module_list:
            return []

        # 确保模块列表按 module_order 排序
        sorted_modules = sorted(module_list, key=lambda x: x.get("module_order", 0))

        # 查询当前计划已有的最大 moduleOrder，避免编号重复
        existing = java_client.get_plan_resources(plan_id)
        max_order = max((r.get("moduleOrder", 0) for r in existing), default=0)

        resources = []
        for mod in sorted_modules:
            module_order_in_list = mod.get("module_order", 0)
            module_type = _normalize_module_type(mod.get("module_type", "text"))

            module_data = {
                "title": mod.get("title", f"模块 {module_order_in_list}"),
                "content": mod.get("content", ""),
                "description": mod.get("description", ""),
                "key_concepts": mod.get("metadata", {}).get("key_concepts", []),
                "module_title": mod.get("title", f"模块 {module_order_in_list}"),
                "estimated_hours": mod.get("estimated_hours", 2),
                "references": mod.get("references", []),
            }
            images = mod.get("images", [])
            if images:
                module_data["images"] = images
            resources.append({
                "planId": plan_id,
                "moduleType": module_type,
                "moduleData": json.dumps(module_data, ensure_ascii=False),
                "moduleOrder": max_order + module_order_in_list,
                "status": 2,
                "generatedByAgent": "content_orchestrator",
            })

        if resources:
            result = java_client.create_resources_bulk(resources)
            resource_ids = [r.get("id") for r in (result or []) if r.get("id")]
            logger.info(f"[资源持久化] 已保存 {len(resources)} 个学习资源到计划 {plan_id}，编号从 {max_order + 1} 开始")
            logger.info(f"[资源持久化] 模块顺序: {[mod.get('module_order') for mod in sorted_modules]}")
            return resource_ids
    except Exception as e:
        logger.warning(f"[资源持久化] 保存模块资源失败: {e}")
    return []


def _save_module_immediately(plan_id: int, module: dict) -> dict | None:
    """立即将单个模块保存为资源记录，返回 {id, type, title} 或 None"""
    try:
        existing = java_client.get_plan_resources(plan_id)
        max_order = max((r.get("moduleOrder", 0) for r in existing), default=0)
        module_order = module.get("module_order", 0)
        module_type = _normalize_module_type(module.get("module_type", "text"))
        module_data = {
            "title": module.get("title", f"模块 {module_order}"),
            "content": module.get("content", ""),
            "description": module.get("description", ""),
            "key_concepts": module.get("metadata", {}).get("key_concepts", []),
            "module_title": module.get("title", f"模块 {module_order}"),
            "estimated_hours": module.get("estimated_hours", 2),
            "references": module.get("references", []),
        }
        images = module.get("images", [])
        if images:
            module_data["images"] = images
        result = java_client.create_resource(
            plan_id=plan_id,
            module_type=module_type,
            module_data=module_data,
            module_order=max_order + module_order,
            status=2,
            generated_by_agent="content_orchestrator",
        )
        res_id = result.get("id") if isinstance(result, dict) else None
        if res_id:
            try:
                res_task = java_client.create_generation_task(
                    plan_id=plan_id, resource_id=res_id, agent_chain="plan_chat",
                )
                if res_task and isinstance(res_task, dict):
                    java_client.update_generation_task(res_task["id"], 2, update_resource_status=False)
            except Exception:
                pass
            return {"id": res_id, "type": module_type, "title": module.get("title", "")}
    except Exception as e:
        logger.warning(f"[即时保存] 保存模块失败: {e}")
    return None


def _save_resource_content(resource_id: int, orchestrated_content: dict = None, module_list: list = None):
    """将生成的资源内容持久化到数据库"""
    try:
        if not orchestrated_content and not module_list:
            return
        result_data = {
            "title": orchestrated_content.get("title", "") if orchestrated_content else "",
            "description": orchestrated_content.get("description", "") if orchestrated_content else "",
            "modules": module_list or (orchestrated_content.get("modules", []) if orchestrated_content else []),
            "summary": orchestrated_content.get("summary", "") if orchestrated_content else "",
        }
        module_data_json = json.dumps(result_data, ensure_ascii=False)
        java_client.update_resource_content(resource_id, module_data_json, 2)
        logger.info(f"[资源持久化] 资源 {resource_id} 内容已保存")
    except Exception as e:
        logger.warning(f"[资源持久化] 保存失败: {e}")


# ─── 流式状态查询端点（用于刷新后恢复流式动画） ───

@router.get("/stream-state")
async def get_stream_state(
    session_id: str = Query(..., description="会话 ID"),
):
    """
    查询当前会话的流式输出状态
    前端刷新后轮询此端点，获取已累积的流式文本并恢复动画
    """
    from app.services.stream_state import get_stream_state as _get_state
    state = _get_state(session_id)
    if state is None:
        return {"data": None}
    return {"data": state}


@router.post("/stop")
async def stop_generation(
    session_id: str = Query(..., description="会话 ID"),
    plan_id: str = Query("", description="学习计划 ID"),
):
    """
    停止指定会话的流式处理
    前端调用后，后台线程会在下一个节点边界检查到停止信号并终止
    """
    request_stop(session_id)
    logger.info(f"[停止] 会话 {session_id} 收到停止请求")

    # 记录一条对话说明用户主动停止
    try:
        plan_id_int = int(plan_id) if plan_id and plan_id.isdigit() else None
        # 从 ticket 获取 user_id（这里简化处理，直接用 session 关联的 user）
        # 由于没有 ticket，暂时只记录到缓存，实际保存由后台线程完成
    except Exception:
        pass

    return {"data": {"status": "stop_requested"}}


@router.get("/proxy-image")
def proxy_image(url: str = Query(..., description="图片 URL")):
    """代理图片请求，返回 base64 data URL，解决 PDF 导出时的 CORS 问题"""
    import base64
    import requests as req
    try:
        resp = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        if ";" in content_type:
            content_type = content_type.split(";")[0].strip()
        b64 = base64.b64encode(resp.content).decode()
        return {"data_url": f"data:{content_type};base64,{b64}"}
    except Exception as e:
        return {"data_url": None, "error": str(e)}
