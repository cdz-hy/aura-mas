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
import asyncio
import threading
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState, NODE_RESOURCE_TYPE_GENERATOR
from app.prompts import QUIZ_GRADER_PROMPT
from app.agents.profile_maintainer import profile_maintainer_node
from app.agents.conversation_compressor import build_chat_history_with_context, async_compress_and_save
from app.schemas.sse_bridge import graph_step_to_sse
from app.utils.profile_utils import ensure_learning_behavior_fields
from app.utils.token_recorder import record_from_mimo

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
            # 默认确认文本 = 用户直接点击确认；其他文本 = 补充说明/反馈
            is_default_confirm = message.strip() == "确认，开始生成学习资源"
            breakdown_confirmed = is_default_confirm
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

    # 预创建占位资源记录（确认分解后，并行生成前）
    placeholder_map = {}
    if breakdown_confirmed and parsed_breakdown and plan_id_int:
        modules = parsed_breakdown.get("modules", [])
        if modules:
            placeholder_map = _create_placeholder_resources(plan_id_int, modules)
            logger.info(f"[占位资源] 已创建 {len(placeholder_map)} 个占位记录")

    # 构造现有 graph 的初始状态
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

    # 后台任务与 SSE 流共享的状态（解耦图执行与客户端连接）
    bg_state = {
        "events": [],           # 待推送的 SSE 事件字符串
        "finished": False,      # 图执行是否完成
        "error": None,          # 异常信息
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

    # SSE 实时回调：节点执行期间直接推送事件到队列
    def _sse_callback(data):
        bg_state["events"].append(data)
    initial_state["sse_callback"] = _sse_callback

    # 创建占位资源的回调（供 content_orchestrator 在单模块自动确认时调用）
    def _create_placeholder_callback(modules: list) -> dict:
        if not plan_id_int or not modules:
            return {}
        placeholder_map = _create_placeholder_resources(plan_id_int, modules)
        if placeholder_map:
            bg_state["placeholder_map"] = placeholder_map
            # 通知前端创建侧栏占位条目
            _sse_callback(
                f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(placeholder_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n'
            )
            logger.info(f"[占位回调] 创建 {len(placeholder_map)} 个占位记录")
        return placeholder_map
    initial_state["create_placeholder_callback"] = _create_placeholder_callback

    def _run_graph_sync():
        """同步执行图工作流（在独立线程中运行，不阻塞事件循环）"""
        try:
            async def _run():
                graph = get_learning_graph()
                logger.info(f"[对话流] 图执行开始 (线程: {threading.current_thread().name})")
                async for event in graph.astream(initial_state, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        logger.info(f"[对话流] 节点完成: {node_name}, sse_callback队列长度: {len(bg_state['events'])}")
                        if node_output is None:
                            continue
                        if isinstance(node_output, dict):
                            if node_output.get("orchestrated_content"):
                                bg_state["orchestrated_content"] = node_output["orchestrated_content"]
                            if node_output.get("module_list"):
                                bg_state["module_list"] = node_output["module_list"]
                                # 即时保存有内容的模块并推送流式更新
                                if plan_id_int:
                                    for mod in node_output["module_list"]:
                                        if mod.get("content") and mod.get("module_order") not in bg_state["saved_module_orders"]:
                                            mod_order = mod.get("module_order")
                                            placeholder = bg_state["placeholder_map"].get(mod_order)
                                            if placeholder:
                                                # 有占位记录 → 更新内容
                                                try:
                                                    module_data = {
                                                        "title": mod.get("title", placeholder.get("title", "")),
                                                        "content": mod.get("content", ""),
                                                        "description": mod.get("description", ""),
                                                        "key_concepts": mod.get("metadata", {}).get("key_concepts", []),
                                                        "module_title": mod.get("title", ""),
                                                        "estimated_hours": mod.get("estimated_hours", 2),
                                                    }
                                                    images = mod.get("images", [])
                                                    if images:
                                                        module_data["images"] = images
                                                    java_client.update_resource_content(
                                                        placeholder["id"],
                                                        json.dumps(module_data, ensure_ascii=False),
                                                        status=2,
                                                    )
                                                    saved = {"id": placeholder["id"], "type": placeholder["type"], "title": mod.get("title", placeholder["title"])}
                                                    bg_state["generated_resource_info"].append(saved)
                                                    bg_state["saved_module_orders"].add(mod_order)
                                                    bg_state["events"].append(
                                                        f'data: {json.dumps({"type": "resource_stream_update", "resource": saved, "content": mod["content"]}, ensure_ascii=False)}\n\n'
                                                    )
                                                except Exception as e:
                                                    logger.warning(f"[占位更新] 更新资源 {placeholder['id']} 失败: {e}")
                                            else:
                                                # 无占位记录 → 创建新记录
                                                saved = _save_module_immediately(plan_id_int, mod)
                                                if saved:
                                                    bg_state["generated_resource_info"].append(saved)
                                                    bg_state["saved_module_orders"].add(mod_order)
                                                    bg_state["events"].append(
                                                        f'data: {json.dumps({"type": "resource_stream_update", "resource": saved, "content": mod["content"]}, ensure_ascii=False)}\n\n'
                                                    )
                            if node_output.get("quiz_questions"):
                                bg_state["quiz_questions"] = node_output["quiz_questions"]
                            if node_output.get("quiz_config"):
                                bg_state["quiz_config"] = node_output["quiz_config"]
                            if node_output.get("generated_content"):
                                bg_state["generated_content"] = node_output["generated_content"]
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
                                # 失败模块：清空占位记录内容，标记为失败
                                for failed_id in failed_module_ids:
                                    placeholder = bg_state["placeholder_map"].get(failed_id)
                                    if placeholder:
                                        try:
                                            java_client.update_resource_content(
                                                placeholder["id"],
                                                json.dumps({"title": placeholder["title"], "content": ""}, ensure_ascii=False),
                                                status=3,
                                            )
                                            bg_state["events"].append(
                                                f'data: {json.dumps({"type": "resource_stream_failed", "resource_id": placeholder["id"]}, ensure_ascii=False)}\n\n'
                                            )
                                            logger.info(f"[审查失败] 模块 {failed_id} 占位记录 {placeholder['id']} 已标记为失败")
                                        except Exception as e:
                                            logger.warning(f"[审查失败] 更新占位记录失败: {e}")
                                # 通过模块：仅保存没有占位记录的（有占位的已在上面更新过）
                                if passed_modules:
                                    unpassed = [m for m in passed_modules
                                                if m.get("module_order") not in bg_state["saved_module_orders"]]
                                    if unpassed:
                                        new_ids = _save_modules_as_resources(plan_id_int, unpassed, None)
                                        for idx, rid in enumerate(new_ids):
                                            mod = unpassed[idx] if idx < len(unpassed) else {}
                                            bg_state["generated_resource_info"].append({
                                                "id": rid,
                                                "type": mod.get("module_type", "document"),
                                                "title": mod.get("title", f"模块 {idx + 1}"),
                                            })
                                            bg_state["saved_module_orders"].add(mod.get("module_order"))
                                        logger.info(f"[增量保存] 已保存 {len(unpassed)} 个无占位的通过模块")
                                    logger.info(f"[增量保存] 审查通过 {len(passed_modules)} 个模块，失败 {len(failed_module_ids)} 个")
                        for sse_data in graph_step_to_sse(node_name, node_output):
                            bg_state["events"].append(sse_data)
                            _persist_profile_update(sse_data, user_id)
                            if '"chunk"' in sse_data:
                                try:
                                    d = json.loads(sse_data.replace("data: ", "").strip())
                                    bg_state["ai_response_parts"].append(d.get("content", ""))
                                except Exception:
                                    pass

            asyncio.run(_run())

            _bg_save_resources()

            if chat_task_id:
                try:
                    java_client.update_generation_task(chat_task_id, 2)
                except Exception:
                    pass

            if bg_state["generated_resource_info"]:
                _async_profile_maintenance_sync(user_id, message, chat_history, user_profile)

            # 会话压缩任务（后台线程，不阻塞响应）
            threading.Thread(target=lambda: asyncio.run(async_compress_and_save(
                user_id=user_id,
                session_id=session_id,
                plan_id=plan_id_int,
            )), daemon=True).start()

            bg_state["events"].append(
                f'data: {json.dumps({"type": "resource_generated", "resources": bg_state["generated_resource_info"]}, ensure_ascii=False)}\n\n'
                if bg_state["generated_resource_info"] else None
            )
            bg_state["events"].append(
                f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
            )

        except Exception as e:
            logger.error(f"[对话流] 后台图执行异常: {e}", exc_info=True)
            bg_state["error"] = str(e)
            bg_state["events"].append(
                f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'
            )
            _bg_save_resources()
            if chat_task_id:
                try:
                    java_client.update_generation_task(chat_task_id, 3)
                except Exception:
                    pass
            _save_plain_text_reply(bg_state["breakdown_confirmed"], bg_state["generated_resource_info"],
                                   bg_state["ai_response_parts"], user_id, session_id, plan_id_int)

        finally:
            bg_state["finished"] = True
            _save_plain_text_reply(bg_state["breakdown_confirmed"], bg_state["generated_resource_info"],
                                   bg_state["ai_response_parts"], user_id, session_id, plan_id_int)

    # 启动独立线程执行图工作流（不阻塞事件循环，SSE 可实时推送）
    threading.Thread(target=_run_graph_sync, daemon=True).start()

    async def stream():
        """SSE 流：从共享队列读取事件并推送给客户端"""
        logger.info(f"[对话流] stream() 开始, 后台线程已启动")
        event_count = 0
        try:
            while True:
                if bg_state["events"]:
                    sse_data = bg_state["events"].pop(0)
                    if sse_data:
                        event_count += 1
                        if '"stream_text"' not in sse_data:
                            logger.info(f"[对话流] yield #{event_count}: {sse_data[:120]}...")
                        yield sse_data
                elif bg_state["finished"]:
                    # 后台完成且队列已空，退出
                    break
                else:
                    await asyncio.sleep(0.05)
            logger.info(f"[对话流] stream() 结束, 共 {event_count} 个事件")
        except GeneratorExit:
            logger.warning(f"[对话流] 客户端断开, 已 {event_count} 个事件")

    def _bg_save_resources():
        """保存后台任务中生成的资源"""
        bs = bg_state

        # 网络搜索资源：将 generated_content 转为 module_list（跳过审查后需要此转换）
        if bs["generated_content"] and not bs["module_list"] and not bs["orchestrated_content"]:
            gc = bs["generated_content"]
            bs["module_list"] = [{
                "module_order": 1,
                "module_id": gc.get("module_id", 1),
                "title": gc.get("title", ""),
                "content": gc.get("content", ""),
                "module_type": gc.get("content_type", "text"),
                "key_points": gc.get("key_points", []),
                "images": gc.get("images", []),
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
                        "type": mod.get("module_type", "document"),
                        "title": mod.get("title", f"模块 {idx + 1}"),
                    })
                    bs["saved_module_orders"].add(mod.get("module_order"))
                logger.info(f"[资源持久化] 保存 {len(new_modules)} 个新增模块")
            if parsed_breakdown and bs["generated_resource_info"]:
                all_ids = [r["id"] for r in bs["generated_resource_info"] if r.get("id")]
                if all_ids:
                    _save_breakdown_dialogue(user_id, session_id, plan_id_int, parsed_breakdown, all_ids)

        # 网络搜索资源（无 task_breakdown 流程）：直接从 module_list 保存
        if not bs["breakdown_confirmed"] and bs["module_list"] and plan_id_int:
            new_modules = [m for m in bs["module_list"]
                           if m.get("module_order") not in bs["saved_module_orders"]]
            if new_modules:
                new_ids = _save_modules_as_resources(plan_id_int, new_modules, bs["orchestrated_content"])
                for idx, rid in enumerate(new_ids):
                    mod = new_modules[idx] if idx < len(new_modules) else {}
                    bs["generated_resource_info"].append({
                        "id": rid,
                        "type": mod.get("module_type", "document"),
                        "title": mod.get("title", f"模块 {idx + 1}"),
                    })
                    bs["saved_module_orders"].add(mod.get("module_order"))
                logger.info(f"[资源持久化] 保存 {len(new_modules)} 个网络搜索资源")

        if bs["quiz_questions"] and plan_id_int:
            quiz_res_id = _save_quiz_resource(plan_id_int, bs["quiz_questions"], bs["quiz_config"])
            if quiz_res_id:
                bs["generated_resource_info"].append({
                    "id": quiz_res_id,
                    "type": "quiz",
                    "title": (bs["quiz_config"] or {}).get("title", "练习题"),
                })

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
    type: str = Query("document", description="资源类型: document/mindmap/quiz/code/summary"),
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
        if isinstance(current_resource, dict):
            current_module_order = current_resource.get("moduleOrder", 0)
            # 提取资源内容全文（moduleData 可能是 JSON 字符串或 dict）
            md = current_resource.get("moduleData")
            if isinstance(md, str):
                try:
                    md = json.loads(md)
                except Exception:
                    md = {}
            if isinstance(md, dict):
                source_resource_content = md.get("content", "")
        logger.info(f"[资源生成] 当前资源 moduleOrder={current_module_order}, 内容长度={len(source_resource_content)}")
    except Exception as e:
        logger.warning(f"[资源生成] 获取当前资源信息失败: {e}")

    # 构造以资源生成为目标的初始状态
    resource_message = f"请为以下模块生成{type}类型的学习资源: {title}"
    if description:
        resource_message += f"\n模块描述: {description}"

    # quiz 和 video 走独立流程，mindmap/summary/code 走类型资源生成，其他走 RAG + 编排
    is_quiz = (type == "quiz")
    is_video = (type == "video")
    is_type_resource = type in ("mindmap", "summary", "code")

    # 路由决策
    if is_quiz:
        intent = "generate_quiz"
        next_node = "quiz_generator"
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
    }

    session_id = effective_session_id

    # 后台任务与 SSE 流共享的状态
    bg_state = {
        "events": [],
        "finished": False,
        "error": None,
        "orchestrated_content": None,
        "module_list": [],
        "quiz_questions": None,
        "quiz_config": None,
        "generated_content": None,
    }

    # SSE 实时回调
    def _sse_callback_rg(data):
        bg_state["events"].append(data)
        logger.debug(f"[资源生成SSE] 入队: {data[:120]}...")
    initial_state["sse_callback"] = _sse_callback_rg

    def _run_graph_sync():
        """同步执行图工作流（在独立线程中运行，不阻塞事件循环）"""
        try:
            # video 类型：直接搜索视频，不走 LangGraph
            if is_video:
                bg_state["events"].append(
                    f'data: {json.dumps({"type": "progress", "content": f"正在搜索「{title}」相关教学视频..."}, ensure_ascii=False)}\n\n'
                )
                videos = _search_videos(title)

                if videos:
                    res_id = _save_video_resource(plan_id_int, videos, current_module_order)
                    if res_id:
                        bg_state["events"].append(
                            f'data: {json.dumps({"type": "resource_generated", "resources": [{"id": res_id, "type": "video", "title": f"{title} - 教学视频"}]}, ensure_ascii=False)}\n\n'
                        )
                else:
                    bg_state["events"].append(
                        f'data: {json.dumps({"type": "progress", "content": "未找到相关教学视频，建议直接在视频平台搜索"}, ensure_ascii=False)}\n\n'
                    )
                bg_state["events"].append(
                    f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
                )
                if generation_task_id:
                    try:
                        java_client.update_generation_task(generation_task_id, 2)
                    except Exception:
                        pass
                return

            # quiz 和其他类型走 LangGraph
            async def _run():
                graph = get_learning_graph()
                async for event in graph.astream(initial_state, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_output is None:
                            continue
                        if isinstance(node_output, dict):
                            if node_output.get("orchestrated_content"):
                                bg_state["orchestrated_content"] = node_output["orchestrated_content"]
                            if node_output.get("module_list"):
                                bg_state["module_list"] = node_output["module_list"]
                                if plan_id_int:
                                    for mod in node_output["module_list"]:
                                        if mod.get("content") and mod.get("module_order") not in bg_state["saved_module_orders"]:
                                            saved = _save_module_immediately(plan_id_int, mod)
                                            if saved:
                                                bg_state["generated_resource_info"].append(saved)
                                                bg_state["saved_module_orders"].add(mod.get("module_order"))
                                                bg_state["events"].append(
                                                    f'data: {json.dumps({"type": "resource_stream_update", "resource": saved, "content": mod["content"]}, ensure_ascii=False)}\n\n'
                                                )
                            if node_output.get("quiz_questions"):
                                bg_state["quiz_questions"] = node_output["quiz_questions"]
                            if node_output.get("quiz_config"):
                                bg_state["quiz_config"] = node_output["quiz_config"]
                            if node_output.get("generated_content"):
                                bg_state["generated_content"] = node_output["generated_content"]
                        for sse_data in graph_step_to_sse(node_name, node_output):
                            bg_state["events"].append(sse_data)
                            _persist_profile_update(sse_data, user_id)

            asyncio.run(_run())

            # 网络搜索资源：将 generated_content 转为 module_list（跳过审查后需要此转换）
            if bg_state["generated_content"] and not bg_state["module_list"] and not bg_state["orchestrated_content"]:
                gc = bg_state["generated_content"]
                bg_state["module_list"] = [{
                    "module_order": 1,
                    "module_id": gc.get("module_id", 1),
                    "title": gc.get("title", ""),
                    "content": gc.get("content", ""),
                    "module_type": gc.get("content_type", "text"),
                    "key_points": gc.get("key_points", []),
                    "images": gc.get("images", []),
                    "description": description,
                }]
                bg_state["orchestrated_content"] = {
                    "title": gc.get("title", ""),
                    "modules": bg_state["module_list"],
                }

            # 图执行完成，保存资源
            generated_resource_info = _persist_generated_resources(
                plan_id_int, user_id, is_quiz, type, title, description,
                bg_state["module_list"], bg_state["orchestrated_content"],
                bg_state["quiz_questions"], bg_state["quiz_config"],
                bg_state["generated_content"],
                current_module_order, session_id,
            )
            if generated_resource_info:
                bg_state["events"].append(
                    f'data: {json.dumps({"type": "resource_generated", "resources": generated_resource_info}, ensure_ascii=False)}\n\n'
                )
            bg_state["events"].append(
                f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
            )

            # 更新生成任务状态为已完成
            if generation_task_id:
                try:
                    java_client.update_generation_task(generation_task_id, 2)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"[资源生成] 后台图执行异常: {e}", exc_info=True)
            bg_state["error"] = str(e)
            bg_state["events"].append(
                f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'
            )
            if not is_video:
                _persist_generated_resources(
                    plan_id_int, user_id, is_quiz, type, title, description,
                    bg_state["module_list"], bg_state["orchestrated_content"],
                    bg_state["quiz_questions"], bg_state["quiz_config"],
                    bg_state["generated_content"],
                    current_module_order, session_id,
                )
            # 更新生成任务状态为失败
            if generation_task_id:
                try:
                    java_client.update_generation_task(generation_task_id, 3)
                except Exception:
                    pass
        finally:
            bg_state["finished"] = True

    # 启动独立线程执行图工作流（不阻塞事件循环，SSE 可实时推送）
    threading.Thread(target=_run_graph_sync, daemon=True).start()

    async def stream():
        logger.info(f"[资源生成] stream() 开始")
        event_count = 0
        try:
            while True:
                if bg_state["events"]:
                    sse_data = bg_state["events"].pop(0)
                    if sse_data:
                        event_count += 1
                        if '"stream_text"' not in sse_data:
                            logger.info(f"[资源生成] yield #{event_count}: {sse_data[:120]}...")
                        yield sse_data
                elif bg_state["finished"]:
                    break
                else:
                    await asyncio.sleep(0.05)
            logger.info(f"[资源生成] stream() 结束, 共 {event_count} 个事件")
        except GeneratorExit:
            logger.warning(f"[资源生成] 客户端断开, 已 {event_count} 个事件")

    return StreamingResponse(
        stream(),
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

        llm = get_quiz_grader_llm()
        total = len(raw_questions)
        correct_count = 0
        details = []

        for i, q in enumerate(raw_questions):
            question_text = q.get("question_text", q.get("question", ""))
            question_type = q.get("question_type", q.get("type", "short_answer"))
            correct_answer = q.get("correct_answer", q.get("correctAnswer", ""))
            explanation = q.get("explanation", "")
            difficulty = q.get("difficulty", 3)

            # 获取用户答案
            raw_ans = user_answers.get(str(i), user_answers.get(i, None))
            if raw_ans is None:
                user_answer_text = "未作答"
            elif isinstance(raw_ans, list):
                # 多选题：索引列表 -> 选项文本
                options = q.get("options", [])
                if options and all(isinstance(a, int) for a in raw_ans):
                    user_answer_text = ", ".join(options[a] for a in raw_ans if a < len(options))
                else:
                    user_answer_text = ", ".join(str(a) for a in raw_ans)
            elif isinstance(raw_ans, int) and q.get("options"):
                # 单选题：索引 -> 选项文本
                opts = q.get("options", [])
                user_answer_text = opts[raw_ans] if raw_ans < len(opts) else str(raw_ans)
            else:
                user_answer_text = str(raw_ans)

            # 推送进度
            yield f'data: {json.dumps({"type": "progress", "content": f"正在批改第 {i + 1}/{total} 题..."}, ensure_ascii=False)}\n\n'

            # 批改 - 所有题型统一走 LLM，生成具体分析
            messages = [
                {"role": "system", "content": QUIZ_GRADER_PROMPT},
                {"role": "user", "content": f"题目: {question_text}\n题型: {question_type}\n参考答案: {correct_answer}\n答案解析: {explanation}\n\n用户回答: {user_answer_text}\n\n请批改并输出 JSON:"},
            ]
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: llm.chat_json(messages, max_tokens=2048))
            except Exception as e:
                logger.error(f"[测验批改] LLM 批改异常: {e}")
                result = {"score": 0, "is_correct": False, "feedback": f"批改异常: {str(e)}", "key_points_hit": [], "key_points_missed": [], "improvement_suggestions": []}

            is_correct_flag = result.get("is_correct", False)
            if is_correct_flag:
                correct_count += 1

            # 保存到 quiz_record 表
            try:
                java_client.create_quiz_record(
                    resource_id=resource_id_int,
                    user_id=user_id,
                    plan_id=plan_id_int,
                    question_type=question_type,
                    correct_answer=str(correct_answer),
                    user_answer=user_answer_text,
                    is_correct=1 if is_correct_flag else 0,
                    difficulty=difficulty,
                )
            except Exception as e:
                logger.warning(f"[测验批改] 保存答题记录失败: {e}")

            detail = {
                "index": i,
                "question": question_text,
                "question_type": question_type,
                "user_answer": user_answer_text,
                "correct_answer": str(correct_answer),
                "score": result.get("score", 0),
                "is_correct": is_correct_flag,
                "feedback": result.get("feedback", ""),
                "key_points_hit": result.get("key_points_hit", []),
                "key_points_missed": result.get("key_points_missed", []),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "explanation": explanation,
            }
            details.append(detail)

            # SSE 推送该题结果
            yield f'data: {json.dumps({"type": "quiz_question_result", "index": i, "result": detail}, ensure_ascii=False)}\n\n'

        # 记录所有批改 LLM 调用的 token 消耗
        record_from_mimo(llm, user_id, "quiz_grading", plan_id_int)

        # 总体结果
        overall_score = round(correct_count / total * 100) if total > 0 else 0
        summary = {
            "score": overall_score,
            "total": total,
            "correct": correct_count,
            "details": details,
        }
        yield f'data: {json.dumps({"type": "quiz_result", "result": summary}, ensure_ascii=False)}\n\n'

        # 将批改结果写入资源的 module_data，下次打开时可直接显示
        try:
            updated_module_data = dict(module_data)
            updated_module_data["latestResult"] = {
                "answers": user_answers,
                "score": overall_score,
                "total": total,
                "correct": correct_count,
                "details": details,
                "submittedAt": datetime.now().isoformat(),
            }
            java_client.update_resource_content(resource_id_int, json.dumps(updated_module_data, ensure_ascii=False))
            logger.info(f"[测验批改] 已将批改结果写入资源 {resource_id_int} 的 module_data")
        except Exception as e:
            logger.warning(f"[测验批改] 写入 module_data 失败: {e}")

        # 后台画像维护（在线程中执行，不阻塞 SSE 流）
        threading.Thread(target=_async_profile_maintenance_sync, kwargs={
            "user_id": user_id,
            "user_message": f"完成测验，得分 {overall_score}",
            "chat_history": [],
            "user_profile": {},
            "quiz_result": summary,
        }, daemon=True).start()

        yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _check_answer(user_answer, correct_answer: str, question_type: str, options: list) -> bool:
    """比对选择/判断题答案"""
    if user_answer is None:
        return False

    if question_type == "single_choice":
        # user_answer 可能是索引(int)或文本(str)
        if isinstance(user_answer, int):
            correct_text = correct_answer.strip()
            # correctAnswer 可能是 "A" 格式或选项文本
            if correct_text in ("A", "B", "C", "D", "E"):
                return "ABCD E".index(correct_text) == user_answer
            # 或者是选项文本
            return options[user_answer].strip() == correct_text if user_answer < len(options) else False
        return str(user_answer).strip().lower() == str(correct_answer).strip().lower()

    elif question_type == "multiple_choice":
        if isinstance(user_answer, list) and options:
            # 索引列表 -> 排序后比对
            selected = sorted(user_answer)
            # correctAnswer 可能是 "A,C" 格式或选项文本列表
            ca = str(correct_answer).strip()
            if all(c in "ABCDE," for c in ca):
                correct_indices = sorted(" ABCDE".index(c) for c in ca.split(",") if c.strip())
                return selected == correct_indices
            # 选项文本比对
            selected_texts = sorted(options[i].strip() for i in selected if i < len(options))
            correct_texts = sorted(t.strip() for t in ca.split(","))
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


def _build_resource_summary(module_list: list, quiz_questions: list = None, orchestrated_content: dict = None) -> str:
    """构建生成资源的简要摘要"""
    parts = []
    if module_list:
        titles = [m.get("title", "") for m in module_list if m.get("title")]
        types = list({m.get("module_type", "document") for m in module_list})
        type_label = "/".join(types)
        parts.append(f"已生成 {len(module_list)} 个{type_label}类型学习模块：{'、'.join(titles)}")
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

    # 类型资源（mindmap/summary/code）：直接从 generated_content 保存
    is_type_resource = resource_type in ("mindmap", "summary", "code")
    if is_type_resource and generated_content and plan_id_int:
        module_data = {
            "title": generated_content.get("title", title),
            "description": generated_content.get("description", description),
            "content": generated_content.get("content", ""),
            "module_title": generated_content.get("title", title),
        }
        try:
            result = java_client.create_resource(
                plan_id=plan_id_int,
                module_type=resource_type,
                module_data=json.dumps(module_data, ensure_ascii=False),
                module_order=current_module_order,
                status=2,
                generated_by_agent="resource_type_generator",
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
            if module_list:
                module_data["content"] = module_list[0].get("content", "") if module_list else ""
                if not module_data.get("title"):
                    module_data["title"] = module_list[0].get("title", title)
                # 传递图片数据
                images = module_list[0].get("images", [])
                if images:
                    module_data["images"] = images
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
        from app.agents.resource_generator import _search_tavily
    except ImportError:
        logger.warning("[视频搜索] 无法导入 _search_tavily")
        return []

    # 中英文双语搜索
    results_cn, _ = _search_tavily(f"{module_title} 教学视频", max_results=5)
    results_en, _ = _search_tavily(f"{module_title} tutorial video", max_results=3)

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
            module_type = "document"
            resources = mod.get("resources", [])
            if resources:
                module_type = resources[0].get("resource_type", "document")
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
            # 使用模块自身的 module_order，而不是 enumerate 的索引
            module_order_in_list = mod.get("module_order", 0)
            
            module_type = mod.get("module_type", "document")
            module_data = {
                "title": mod.get("title", f"模块 {module_order_in_list}"),
                "content": mod.get("content", ""),
                "description": mod.get("description", ""),
                "key_concepts": mod.get("metadata", {}).get("key_concepts", []),
                "module_title": mod.get("title", f"模块 {module_order_in_list}"),
                "estimated_hours": mod.get("estimated_hours", 2),
            }
            # 传递图片数据
            images = mod.get("images", [])
            if images:
                module_data["images"] = images
            resources.append({
                "planId": plan_id,
                "moduleType": module_type,
                "moduleData": json.dumps(module_data, ensure_ascii=False),
                "moduleOrder": max_order + module_order_in_list,  # 使用模块自身的顺序
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
        module_type = module.get("module_type", "document")
        module_data = {
            "title": module.get("title", f"模块 {module_order}"),
            "content": module.get("content", ""),
            "description": module.get("description", ""),
            "key_concepts": module.get("metadata", {}).get("key_concepts", []),
            "module_title": module.get("title", f"模块 {module_order}"),
            "estimated_hours": module.get("estimated_hours", 2),
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
