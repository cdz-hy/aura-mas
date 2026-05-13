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
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState
from app.agents.profile_maintainer import profile_maintainer_node
from app.schemas.sse_bridge import graph_step_to_sse
from app.utils.profile_utils import ensure_learning_behavior_fields

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

    human_feedback = None
    if not breakdown_confirmed and parsed_breakdown:
        human_feedback = message

    # 构造现有 graph 的初始状态
    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id_int,
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
    }

    async def stream():
        nonlocal breakdown_confirmed
        ai_response_parts = []
        module_list = []
        orchestrated_content = None
        quiz_questions = None
        quiz_config = None
        new_breakdown = None
        generated_resource_info = []  # 收集生成的资源信息 [{id, type, title}]
        saved_module_orders = set()  # 已增量保存的 module_order（防重复）

        def _save_remaining_resources():
            """保存剩余未持久化的资源（正常完成或客户端断开时调用）"""
            nonlocal generated_resource_info

            # 任务分解生成后保存到 ai_dialogue
            if new_breakdown and plan_id_int and not breakdown_confirmed:
                _save_breakdown_dialogue(user_id, session_id, plan_id_int, new_breakdown)

            # 用户确认后，将生成的学习资源保存到数据库
            if breakdown_confirmed and plan_id_int:
                new_modules = [m for m in module_list
                               if m.get("module_order") not in saved_module_orders]
                if new_modules:
                    new_ids = _save_modules_as_resources(plan_id_int, new_modules, orchestrated_content)
                    for idx, rid in enumerate(new_ids):
                        mod = new_modules[idx] if idx < len(new_modules) else {}
                        generated_resource_info.append({
                            "id": rid,
                            "type": mod.get("module_type", "document"),
                            "title": mod.get("title", f"模块 {idx + 1}"),
                        })
                        saved_module_orders.add(mod.get("module_order"))
                    logger.info(f"[资源持久化] 保存 {len(new_modules)} 个新增模块 (已跳过 {len(saved_module_orders) - len(new_modules)} 个已保存的)")
                if parsed_breakdown and generated_resource_info:
                    all_ids = [r["id"] for r in generated_resource_info if r.get("id")]
                    if all_ids:
                        _save_breakdown_dialogue(user_id, session_id, plan_id_int, parsed_breakdown, all_ids)

            # 题目生成后，保存到学习资源库
            if quiz_questions and plan_id_int:
                quiz_res_id = _save_quiz_resource(plan_id_int, quiz_questions, quiz_config)
                if quiz_res_id:
                    generated_resource_info.append({
                        "id": quiz_res_id,
                        "type": "quiz",
                        "title": (quiz_config or {}).get("title", "练习题"),
                    })

            # 保存结构化的 AI 对话记录
            if generated_resource_info and plan_id_int:
                summary = _build_resource_summary(module_list, quiz_questions, orchestrated_content)
                dialogue_data = {
                    "type": "resource_generated",
                    "summary": summary,
                    "resources": generated_resource_info,
                }
                try:
                    result = java_client.create_dialogue(
                        user_id=user_id,
                        session_id=session_id,
                        conversation_text=json.dumps(dialogue_data, ensure_ascii=False),
                        dialogue_type="AI",
                        plan_id=plan_id_int,
                        intent_type="resource_generated",
                    )
                    dialogue_id = result.get("data", {}).get("id") if isinstance(result, dict) else None
                    if dialogue_id and generated_resource_info:
                        min_resource_id = min(r["id"] for r in generated_resource_info if r.get("id"))
                        try:
                            java_client.update_dialogue_resource_id(dialogue_id, min_resource_id)
                            logger.info(f"[资源生成对话] 已关联资源ID: {min_resource_id}")
                        except Exception as e:
                            logger.warning(f"[资源生成对话] 关联资源ID失败: {e}")
                except Exception as e:
                    logger.warning(f"记录资源生成对话失败: {e}")

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
                        # 收集新生成的任务分解
                        tb = node_output.get("task_breakdown")
                        if tb and node_name == "task_decomposer":
                            new_breakdown = tb
                        # 任务分解节点自动确认时（单模块），同步 breakdown_confirmed
                        if "task_breakdown_confirmed" in node_output:
                            breakdown_confirmed = node_output["task_breakdown_confirmed"]
                        # 检查是否为部分审查失败 → 立即保存已通过模块
                        if (node_name == "review_orchestrate"
                                and not node_output.get("review_passed")
                                and node_output.get("retry_module_ids")
                                and node_output.get("passed_module_list")
                                and plan_id_int
                                and breakdown_confirmed):
                            passed_modules = node_output["passed_module_list"]
                            if passed_modules:
                                new_ids = _save_modules_as_resources(plan_id_int, passed_modules, None)
                                for idx, rid in enumerate(new_ids):
                                    mod = passed_modules[idx] if idx < len(passed_modules) else {}
                                    generated_resource_info.append({
                                        "id": rid,
                                        "type": mod.get("module_type", "document"),
                                        "title": mod.get("title", f"模块 {idx + 1}"),
                                    })
                                    saved_module_orders.add(mod.get("module_order"))
                                logger.info(f"[增量保存] 已保存 {len(passed_modules)} 个通过审查的模块，ID: {new_ids} (orders: {saved_module_orders})")
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

            # 正常完成：保存资源并通知前端
            _save_remaining_resources()

            if generated_resource_info:
                yield f'data: {json.dumps({"type": "resource_generated", "resources": generated_resource_info}, ensure_ascii=False)}\n\n'
                asyncio.create_task(_async_profile_maintenance(
                    user_id=user_id,
                    user_message=message,
                    chat_history=chat_history,
                    user_profile=user_profile,
                    quiz_result=None,
                ))
                logger.info(f"[画像维护] 已触发后台异步更新任务")

            yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'

        except GeneratorExit:
            # 客户端断开连接，确保资源仍然持久化
            logger.warning(f"[对话流] 客户端断开连接，继续保存生成结果...")
            _save_remaining_resources()
            _save_plain_text_reply(breakdown_confirmed, generated_resource_info,
                                   ai_response_parts, user_id, session_id, plan_id_int)
            return

        except Exception as e:
            logger.error(f"对话流异常: {e}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)}\n\n'

        # 未生成资源时，保存纯文本 AI 回复
        _save_plain_text_reply(breakdown_confirmed, generated_resource_info,
                               ai_response_parts, user_id, session_id, plan_id_int)

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

    # 构造以资源生成为目标的初始状态
    resource_message = f"请为以下模块生成{type}类型的学习资源: {title}"
    if description:
        resource_message += f"\n模块描述: {description}"

    # quiz 类型走题目生成智能体，其他类型走 RAG + 编排流程
    is_quiz = (type == "quiz")

    initial_state: AgentState = {
        "user_id": user_id,
        "plan_id": plan_id_int,
        "session_id": f"resource-{plan_id_int}-{module_id_int}",
        "user_message": resource_message,
        "human_feedback": None,
        "chat_history": chat_history,
        "user_profile": user_profile,
        "intent": "generate_quiz" if is_quiz else "generate_resource",
        "next_node": "quiz_generator" if is_quiz else "rag_retriever",
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
    }

    async def stream():
        orchestrated_content = None
        module_list = []
        quiz_questions = None
        quiz_config = None

        # 获取当前资源的 moduleOrder，补充资源使用相同编号
        current_module_order = 0
        try:
            current_resource = java_client.get_resource_by_id(module_id_int)
            if isinstance(current_resource, dict):
                current_module_order = current_resource.get("moduleOrder", 0)
            logger.info(f"[资源生成] 当前资源 moduleOrder={current_module_order}")
        except Exception as e:
            logger.warning(f"[资源生成] 获取当前资源信息失败: {e}")

        session_id = f"resource-{plan_id_int}-{module_id_int}"

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
                    for sse_data in graph_step_to_sse(node_name, node_output):
                        yield sse_data
                        _persist_profile_update(sse_data, user_id)

            # 正常完成：通知前端
            generated_resource_info = _persist_generated_resources(
                plan_id_int, user_id, is_quiz, type, title, description,
                module_list, orchestrated_content, quiz_questions, quiz_config,
                current_module_order, session_id,
            )
            if generated_resource_info:
                yield f'data: {json.dumps({"type": "resource_generated", "resources": generated_resource_info}, ensure_ascii=False)}\n\n'
            yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'

        except GeneratorExit:
            # 客户端断开连接，确保资源仍然持久化
            logger.warning(f"[资源生成] 客户端断开连接，继续保存生成结果...")
            _persist_generated_resources(
                plan_id_int, user_id, is_quiz, type, title, description,
                module_list, orchestrated_content, quiz_questions, quiz_config,
                current_module_order, session_id,
            )
            return

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

        GRADER_PROMPT = """你是一个严格的题目批改专家。根据参考答案评判用户的回答，给出公正准确的评分。

## 评分标准
1. 选择题/判断题: 完全正确得1分，否则0分
2. 填空题: 关键词匹配，部分正确可给0.5分
3. 简答题: 核心概念准确性(40%) + 逻辑完整性(30%) + 表达清晰度(15%) + 补充有价值的额外信息(15%)

## 改进建议要求（重要）
当用户答错时，improvement_suggestions 必须：
- 具体分析用户选错的答案为什么是错的（用户可能存在的误解或知识盲区）
- 对比正确答案和错误答案的差异，指出用户混淆了什么概念
- 给出具体的学习方向，而不是泛泛地说"请复习相关知识点"
- 例如：不要写"请重新审题"，而要写"你可能混淆了HTTP/1.0的短连接和HTTP/1.1的持久连接，建议重点理解两者的区别"

## 输出格式
严格输出 JSON：
{"score": 0-1的浮点数, "is_correct": true/false(score>=0.6为true), "feedback": "简短批改结果(一句话)", "key_points_hit": ["命中的知识点"], "key_points_missed": ["遗漏的知识点"], "improvement_suggestions": ["针对用户错误答案的具体分析和改进建议"]}"""

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
                {"role": "system", "content": GRADER_PROMPT},
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

        # 异步画像维护
        asyncio.create_task(_async_profile_maintenance(
            user_id=user_id,
            user_message=f"完成测验，得分 {overall_score}",
            chat_history=[],
            user_profile={},
            quiz_result=summary,
        ))

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
    current_module_order: int,
    session_id: str,
) -> list:
    """将生成的资源持久化到数据库（与 SSE 解耦，确保断开连接时也能保存）"""
    generated_resource_info = []

    if is_quiz:
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


async def _async_profile_maintenance(
    user_id: int,
    user_message: str,
    chat_history: list,
    user_profile: dict,
    quiz_result: dict = None,
):
    """
    异步执行画像维护，不阻塞主流程
    
    在资源生成完成、题目判定完成等场景下，在后台异步更新用户画像，
    避免阻塞流式输出的结束，提升用户体验。
    """
    try:
        logger.info(f"[画像维护] 开始后台异步更新用户 {user_id} 的画像")
        
        # 构造状态
        state = {
            "user_message": user_message,
            "chat_history": chat_history,
            "user_profile": user_profile,
            "quiz_result": quiz_result,
        }
        
        # 调用画像维护智能体
        result = profile_maintainer_node(state)
        
        # 持久化画像更新
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
        logger.error(f"[画像维护] 异步更新失败: {str(e)}", exc_info=True)


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
