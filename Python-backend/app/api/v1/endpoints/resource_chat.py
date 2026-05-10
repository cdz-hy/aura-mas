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

    # 获取对话历史（按当前会话隔离）
    chat_history = []
    try:
        history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id_int, session_id=session_id, limit=30
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
        module_list = []
        orchestrated_content = None
        quiz_questions = None
        quiz_config = None
        try:
            graph = get_learning_graph()
            async for event in graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    # 收集编排结果用于持久化
                    if isinstance(node_output, dict):
                        if node_output.get("orchestrated_content"):
                            orchestrated_content = node_output["orchestrated_content"]
                        if node_output.get("module_list"):
                            module_list = node_output["module_list"]
                        if node_output.get("quiz_questions"):
                            quiz_questions = node_output["quiz_questions"]
                        if node_output.get("quiz_config"):
                            quiz_config = node_output["quiz_config"]
                    # 使用 sse_bridge 翻译 graph 事件为前端格式
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data
                        # 持久化画像更新
                        _persist_profile_update(sse_data, user_id)
                        # 收集 AI 回复文本
                        if '"chunk"' in sse_data:
                            try:
                                d = json.loads(sse_data.replace("data: ", "").strip())
                                ai_response_parts.append(d.get("content", ""))
                            except Exception:
                                pass

            # 用户确认后，将生成的学习资源保存到数据库
            if breakdown_confirmed and plan_id_int:
                resource_ids = _save_modules_as_resources(plan_id_int, module_list, orchestrated_content)
                # 保存任务分解为对话记录并关联资源ID
                if parsed_breakdown:
                    _save_breakdown_dialogue(user_id, session_id, plan_id_int, parsed_breakdown, resource_ids)

            # 题目生成后，保存到学习资源库
            if quiz_questions and plan_id_int:
                _save_quiz_resource(plan_id_int, quiz_questions, quiz_config)

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
        orchestrated_content = None
        module_list = []
        try:
            graph = get_learning_graph()
            async for event in graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_output is None:
                        continue
                    # 收集编排结果用于持久化
                    if isinstance(node_output, dict):
                        if node_output.get("orchestrated_content"):
                            orchestrated_content = node_output["orchestrated_content"]
                        if node_output.get("module_list"):
                            module_list = node_output["module_list"]
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data
                        _persist_profile_update(sse_data, user_id)

            # 持久化生成的资源内容到数据库
            _save_resource_content(module_id_int, orchestrated_content, module_list)

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


def _persist_profile_update(sse_data: str, user_id: int):
    """从 SSE 事件中提取画像更新并持久化到数据库"""
    try:
        if '"profile_update"' not in sse_data:
            return
        d = json.loads(sse_data.replace("data: ", "").strip())
        if d.get("type") != "profile_update":
            return
        dimensions = d.get("dimensions", {})
        updates = dimensions.get("updates")
        if not updates:
            return
        reason = dimensions.get("reason", "对话分析自动更新")
        logger.info(f"[画像持久化] 保存用户 {user_id} 的画像更新: {reason}")
        java_client.save_user_profile(user_id, updates, reason)
        logger.info(f"[画像持久化] 画像保存成功")
    except Exception as e:
        logger.warning(f"[画像持久化] 保存失败: {e}")


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


def _save_quiz_resource(plan_id: int, questions: list, quiz_config: dict = None):
    """将生成的题目保存为 quiz 类型的学习资源"""
    try:
        if not questions:
            return
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
                    "points": 20,
                }
                for i, q in enumerate(questions)
            ],
            "totalPoints": len(questions) * 20,
            "estimatedMinutes": len(questions) * 2,
        }
        # 获取当前计划最大的 moduleOrder
        existing = java_client.get_plan_resources(plan_id)
        max_order = max((r.get("moduleOrder", 0) for r in existing), default=0)
        java_client.create_resource(
            plan_id=plan_id,
            module_type="quiz",
            module_data=json.dumps(module_data, ensure_ascii=False),
            module_order=max_order + 1,
            status=2,
            generated_by_agent="quiz_generator",
        )
        logger.info(f"[资源持久化] 已保存题目资源到计划 {plan_id}，共 {len(questions)} 题")
    except Exception as e:
        logger.warning(f"[资源持久化] 保存题目资源失败: {e}")


def _save_modules_as_resources(plan_id: int, module_list: list, orchestrated_content: dict = None) -> list:
    """将确认后的学习模块保存为 learning_resource 记录，返回创建的资源ID列表"""
    try:
        if not module_list:
            return []
        resources = []
        for i, mod in enumerate(module_list):
            module_type = mod.get("module_type", "document")
            module_data = {
                "title": mod.get("title", f"模块 {i + 1}"),
                "content": mod.get("content", ""),
                "description": mod.get("description", ""),
                "key_concepts": mod.get("metadata", {}).get("key_concepts", []),
                "module_title": mod.get("title", f"模块 {i + 1}"),
                "estimated_hours": mod.get("estimated_hours", 2),
            }
            resources.append({
                "planId": plan_id,
                "moduleType": module_type,
                "moduleData": json.dumps(module_data, ensure_ascii=False),
                "moduleOrder": mod.get("order", i + 1),
                "status": 2,
                "generatedByAgent": "content_orchestrator",
            })
        if resources:
            result = java_client.create_resources_bulk(resources)
            resource_ids = [r.get("id") for r in (result or []) if r.get("id")]
            logger.info(f"[资源持久化] 已保存 {len(resources)} 个学习资源到计划 {plan_id}")
            return resource_ids
    except Exception as e:
        logger.warning(f"[资源持久化] 保存模块资源失败: {e}")
    return []


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
