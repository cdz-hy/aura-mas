"""
主控智能体 - 负责意图识别和任务调度
在不同情况下调度不同智能体，控制整个进度和流程
"""
import logging
import threading
from typing import Dict, Any
from langgraph.graph import END
from app.agents.schemas import (
    AgentState, NODE_CONTROLLER, NODE_TASK_DECOMPOSER, NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER, NODE_QUIZ_GENERATOR, NODE_QUIZ_GRADER,
    NODE_RESOURCE_GENERATOR, NODE_RESOURCE_TYPE_GENERATOR, NODE_ANIMATION_SKILL_GENERATOR,
    NODE_HUMAN_CONFIRM,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP,
)
from app.agents.llm_factory import get_controller_llm
from app.prompts import CONTROLLER_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.services.db.java_client import java_client

logger = logging.getLogger("agents.controller")


def _classify_goal_action(prev_goal: str, new_goal: str) -> str:
    """根据前后目标推断动作类型，作为 history 元数据"""
    if not prev_goal:
        return "extract"
    if new_goal in prev_goal or prev_goal in new_goal:
        return "refine"
    return "switch"


def _persist_goal_async(plan_id: int, session_id: str, goal: str, action: str, reasoning: str):
    """后台线程异步持久化 learning_goal，不阻塞图执行"""
    def _do_persist():
        try:
            java_client.upsert_session_learning_goal(
                plan_id=plan_id,
                session_id=session_id,
                goal=goal,
                action=action,
                reasoning=reasoning,
            )
            logger.info(f"  [主控智能体] learning_goal 已持久化到 plan={plan_id} session={session_id}")
        except Exception as e:
            logger.warning(f"  [主控智能体] learning_goal 持久化失败 (非致命): {e}")

    threading.Thread(target=_do_persist, daemon=True).start()


def controller_node(state: AgentState) -> Dict[str, Any]:
    """主控智能体节点 - 意图识别与路由"""
    user_message = state.get("user_message", "")
    iteration = state.get("iteration_count", 0)

    logger.info(f"{'='*60}")
    logger.info(f"  [主控智能体] 开始处理 (迭代: {iteration})")
    logger.info(f"  用户输入: {user_message[:100]}")
    logger.info(f"{'='*60}")

    # 智能体自主异常检测：任何智能体发现内容偏离，中断回到主控，主控转入追问模式
    if state.get("agent_anomaly"):
        anomaly_reason = state.get("anomaly_reason", "未知原因")
        logger.warning(f"  [主控智能体] 智能体报告异常: {anomaly_reason}")
        logger.warning(f"  [主控智能体] -> 转入简答追问模式，向用户澄清需求")
        return {
            "intent": INTENT_FOLLOW_UP,
            "next_node": NODE_SIMPLE_ANSWER,
            "agent_anomaly": False,  # 清除异常标记（避免路由死循环）
            "anomaly_clarify": True,  # 简答智能体用此标记进入追问澄清模式
            "anomaly_reason": anomaly_reason,
            "current_step": f"主控智能体: 智能体报告处理异常，转入追问澄清模式",
            "iteration_count": iteration + 1,
            "stream_events": [{
                "event_type": "thinking",
                "agent": "controller",
                "data": {"message": f"检测到处理异常: {anomaly_reason}，将向用户追问澄清需求"},
                "step_description": f"异常中断: {anomaly_reason}"
            }],
        }

    # 检查是否有需要重试的模块（模块级别重试）
    retry_module_ids = state.get("retry_module_ids", [])
    rag_retry_count = state.get("rag_retry_count", 0)
    gen_retry_count = state.get("gen_retry_count", 0)
    max_rag_retries = 1    # RAG 最多重试 1 次
    max_gen_retries = 2    # 自主生成最多重试 2 次

    # 兼容旧的 retry_count 字段
    old_retry_count = state.get("retry_count", 0)
    if old_retry_count > 0 and rag_retry_count == 0 and gen_retry_count == 0:
        rag_retry_count = old_retry_count

    if retry_module_ids:
        # ===== 自主生成阶段：已经走过自主生成但审查仍不通过 =====
        if gen_retry_count > 0:
            if gen_retry_count >= max_gen_retries:
                logger.warning(f"  [主控智能体] 自主生成已重试 {gen_retry_count} 次仍不通过，放弃重试")
                # 收集已通过的模块和最后一次生成的内容，尽量返回给用户
                passed_modules = state.get("passed_modules", [])
                module_list = state.get("module_list", [])
                last_generated = state.get("generated_content")
                available = module_list or []
                if not available and last_generated:
                    # 没有已通过的模块，但有最后一次自主生成的原始内容，直接返回
                    return {
                        "intent": "retry_failed",
                        "next_node": END,
                        "generated_content": last_generated,
                        "current_step": f"审查未通过（已重试 {gen_retry_count} 次），以下为最后一次生成的内容供参考",
                        "retry_module_ids": [],
                        "retry_mode": False,
                        "iteration_count": iteration + 1,
                        "stream_events": [{
                            "event_type": "warning",
                            "agent": "controller",
                            "data": {"message": f"内容审查未通过（已重试 {gen_retry_count} 次），返回最后一次生成结果供参考"},
                            "step_description": "审查未通过，返回最后生成内容"
                        }],
                    }
                if available:
                    return {
                        "intent": "retry_failed",
                        "next_node": END,
                        "module_list": available,
                        "current_step": f"部分模块审查未通过（已重试 {gen_retry_count} 次），已通过的模块已返回",
                        "retry_module_ids": [],
                        "retry_mode": False,
                        "iteration_count": iteration + 1,
                        "stream_events": [{
                            "event_type": "warning",
                            "agent": "controller",
                            "data": {"message": f"有 {len(retry_module_ids)} 个模块审查始终未通过（已重试 {gen_retry_count} 次），已返回 {len(available)} 个通过的模块"},
                            "step_description": "部分模块放弃，返回已通过模块"
                        }],
                    }
                # 什么都没有
                return {
                    "intent": "retry_failed",
                    "next_node": END,
                    "current_step": f"自主生成重试 {gen_retry_count} 次仍未通过审查，且无可用内容",
                    "retry_module_ids": [],
                    "retry_mode": False,
                    "iteration_count": iteration + 1,
                    "stream_events": [{
                        "event_type": "error",
                        "agent": "controller",
                        "data": {"message": "内容生成失败，多次审查均未通过"},
                        "step_description": "内容生成失败"
                    }],
                }
            logger.info(f"  [主控智能体] 自主生成第 {gen_retry_count} 次审查未通过 -> 再次自主生成 (第 {gen_retry_count + 1} 次)")
            return {
                "intent": INTENT_GENERATE_RESOURCE,
                "next_node": NODE_RESOURCE_GENERATOR,
                "retry_mode": True,
                "target_module_ids": retry_module_ids,
                "gen_retry_count": gen_retry_count + 1,
                "current_step": f"主控智能体: 自主生成重试 (第 {gen_retry_count + 1}/{max_gen_retries} 次)",
                "iteration_count": iteration + 1,
            }

        # ===== RAG 阶段：分析审查反馈，判断是否值得重试 RAG =====
        failed_modules = state.get("failed_modules", [])
        total_modules = len(state.get("module_list", [])) + len(failed_modules)
        all_failed = len(retry_module_ids) == total_modules and total_modules > 0

        # 计算未通过模块的平均分和审查反馈
        failed_scores = [m.get("score", 0) for m in failed_modules if "score" in m]
        avg_score = sum(failed_scores) / len(failed_scores) if failed_scores else 0
        failed_feedbacks = [m.get("feedback", "") for m in failed_modules if m.get("feedback")]

        logger.info(f"  [主控智能体] 审查分析: 全部失败={all_failed}, 平均分={avg_score:.1f}, "
                     f"未通过模块数={len(retry_module_ids)}/{total_modules}")

        # 判断 RAG 是否值得重试
        rag_worth_retry = True
        reason = ""

        if all_failed and avg_score < 30:
            rag_worth_retry = False
            reason = f"所有模块均未通过且平均分仅 {avg_score:.1f}，RAG 检索内容与主题完全不相关"
        elif all_failed and avg_score < 50:
            combined_feedback = " ".join(failed_feedbacks).lower()
            irrelevance_keywords = ["不相关", "无关", "不匹配", "缺失", "没有涉及", "未涉及", "完全偏离", "缺乏"]
            match_count = sum(1 for kw in irrelevance_keywords if kw in combined_feedback)
            if match_count >= 2:
                rag_worth_retry = False
                reason = f"审查反馈多次提及内容不相关/缺失（匹配 {match_count} 个关键词），向量库可能无对应知识"
            else:
                reason = f"所有模块失败但平均分 {avg_score:.1f}，内容部分相关，尝试优化检索词重试"
        else:
            reason = f"部分模块未通过或分数尚可（均分 {avg_score:.1f}），RAG 检索可能命中更优结果"

        # 不值得重试 RAG → 直接走自主生成
        if not rag_worth_retry:
            logger.info(f"  [主控智能体] 跳过 RAG 重试: {reason}")
            logger.info(f"  [主控智能体] -> 直接切换到自主生成+网络搜索")
            return {
                "intent": INTENT_GENERATE_RESOURCE,
                "next_node": NODE_RESOURCE_GENERATOR,
                "retry_mode": True,
                "target_module_ids": retry_module_ids,
                "gen_retry_count": 1,
                "current_step": f"主控智能体: {reason}，跳过 RAG 直接自主生成",
                "iteration_count": iteration + 1,
            }

        # 已经重试过 RAG → 切换到自主生成
        if rag_retry_count >= max_rag_retries:
            logger.info(f"  [主控智能体] RAG 已重试 {rag_retry_count} 次仍不通过 -> 切换到自主生成")
            return {
                "intent": INTENT_GENERATE_RESOURCE,
                "next_node": NODE_RESOURCE_GENERATOR,
                "retry_mode": True,
                "target_module_ids": retry_module_ids,
                "gen_retry_count": 1,
                "current_step": f"主控智能体: RAG 重试无效，切换到自主生成模式",
                "iteration_count": iteration + 1,
            }

        logger.info(f"  [主控智能体] 检测到需要重试的模块: {retry_module_ids}")
        logger.info(f"  [主控智能体] RAG 重试次数: {rag_retry_count}/{max_rag_retries}")
        logger.info(f"  [主控智能体] 决策: {reason}")

        # 值得重试 RAG
        return {
            "intent": "retry_modules",
            "next_node": NODE_RAG_RETRIEVER,
            "retry_mode": True,
            "target_module_ids": retry_module_ids,
            "rag_retry_count": rag_retry_count + 1,
            "current_step": f"主控智能体: RAG 重试 (第 {rag_retry_count + 1}/{max_rag_retries} 次)，模块 {retry_module_ids}",
            "iteration_count": iteration + 1,
        }

    # 检测 RAG 批量审查失败
    review_passed = state.get("review_passed", True)
    rag_error = state.get("error")
    if (not review_passed
            and rag_error
            and state.get("task_breakdown")
            and state.get("task_breakdown_confirmed")):
        # 批量审查不通过 → 向量库大概率无相关内容，直接自主生成
        logger.info(f"  [主控智能体] RAG 批量审查未通过({rag_error[:60]}) -> 直接自主生成+网络搜索")
        return {
            "intent": INTENT_GENERATE_RESOURCE,
            "next_node": NODE_RESOURCE_GENERATOR,
            "gen_retry_count": 1,
            "current_step": f"RAG 批量审查未通过，直接启动自主生成（含网络搜索）",
            "iteration_count": iteration + 1,
        }

    # 快速路径：如果前端已确认任务分解，直接进入 RAG 检索，无需 LLM 分类
    # 但如果初始状态已指定 intent（如 generate_quiz / generate_type_resource / generate_animation），按指定意图路由
    preset_intent = state.get("intent", "")
    if state.get("task_breakdown_confirmed") and state.get("task_breakdown"):
        # 快速路径跳过 LLM，需从 checkpoint 恢复 learning_goal
        checkpoint_goal = state.get("_checkpoint_learning_goal", "")
        goal_patch = {"learning_goal": checkpoint_goal} if checkpoint_goal else {}

        if preset_intent == INTENT_GENERATE_QUIZ:
            logger.info(f"  [主控智能体] 预设意图: generate_quiz，路由 -> 题目生成智能体")
            return {
                "intent": INTENT_GENERATE_QUIZ,
                "next_node": NODE_QUIZ_GENERATOR,
                "current_step": "预设意图: 生成题目",
                "iteration_count": iteration + 1,
                **goal_patch,
            }
        if preset_intent == "generate_type_resource":
            logger.info(f"  [主控智能体] 预设意图: generate_type_resource，路由 -> 类型资源生成智能体")
            return {
                "intent": "generate_type_resource",
                "next_node": NODE_RESOURCE_TYPE_GENERATOR,
                "current_step": "预设意图: 生成类型资源",
                "iteration_count": iteration + 1,
                **goal_patch,
            }
        if preset_intent == "generate_animation":
            logger.info(f"  [主控智能体] 预设意图: generate_animation，路由 -> 动画生成智能体")
            return {
                "intent": "generate_animation",
                "next_node": NODE_ANIMATION_SKILL_GENERATOR,
                "current_step": "预设意图: 生成动画",
                "iteration_count": iteration + 1,
                **goal_patch,
            }
        logger.info(f"  [主控智能体] 任务分解已确认，快速路由 -> RAG 检索")
        return {
            "intent": INTENT_GENERATE_RESOURCE,
            "next_node": NODE_RAG_RETRIEVER,
            "current_step": "任务分解已确认，开始检索学习资源",
            "iteration_count": iteration + 1,
            **goal_patch,
        }

    llm = get_controller_llm()

    # 构造对话上下文
    history_text = ""
    chat_history = state.get("chat_history", [])
    if chat_history:
        recent = chat_history[-20:]  # 最近20轮
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            history_text += f"{role}: {msg['content']}\n"
        logger.info(f"  [主控智能体] 对话历史: {len(chat_history)} 轮 (使用最近 {len(recent)} 轮)")

    has_task_breakdown = state.get("task_breakdown") is not None
    has_rag_results = bool(state.get("rag_results"))
    needs_confirm = state.get("needs_human_confirm", False)
    checkpoint_goal = state.get("_checkpoint_learning_goal", "")

    # 上下文增强：告知主控当前状态
    context_info = ""
    if checkpoint_goal:
        context_info += f"\n[上一轮 learning_goal] {checkpoint_goal}"
    if has_task_breakdown:
        context_info += "\n[系统状态] 当前已有任务分解结果，等待用户确认或补充。"
    if has_rag_results:
        context_info += "\n[系统状态] 当前已有 RAG 检索结果。"
    if needs_confirm and state.get("human_feedback"):
        context_info += "\n[系统状态] 用户已给出确认/补充反馈。"

    if context_info:
        logger.info(f"  [主控智能体] 系统状态: {context_info.strip()}")

    messages = [
        {"role": "system", "content": CONTROLLER_PROMPT},
        {"role": "user", "content": f"对话历史:\n{history_text}\n{context_info}\n\n当前用户输入: {user_message}\n\n请综合判断意图与 learning_goal，输出 JSON:"}
    ]

    try:
        logger.info(f"  [主控智能体] 正在流式调用 LLM 进行意图识别与目标管理...")

        intent = None
        reasoning = ""
        managed_learning_goal = None  # LLM 智能管理后的 learning_goal
        accumulated_text = ""

        # 流式收集完整 JSON（不再早退，因为 learning_goal 在 intent 之后输出）
        # 早退判定改为：检测到 JSON 结束符 } 即可
        for chunk in llm.chat_stream(messages, temperature=0.2):
            accumulated_text += chunk
            # 检测 JSON 完整结束（含 intent + learning_goal + reasoning）
            if accumulated_text.count("{") > 0 and accumulated_text.count("}") >= accumulated_text.count("{"):
                # 试探性解析，成功即可早退
                try:
                    import json
                    start = accumulated_text.find('{')
                    end = accumulated_text.rfind('}') + 1
                    candidate = accumulated_text[start:end]
                    parsed = json.loads(candidate)
                    if "intent" in parsed and "learning_goal" in parsed:
                        intent = parsed.get("intent", INTENT_AMBIGUOUS)
                        managed_learning_goal = parsed.get("learning_goal", "").strip()
                        reasoning = parsed.get("reasoning", "")
                        logger.info(f"  [主控智能体] 流式判断: 完整 JSON 已收齐，提前退出!")
                        break
                except Exception:
                    pass  # JSON 还未完整，继续累积

        # 如果流式过程没有解析成功，尝试最后再解析一次
        if intent is None:
            try:
                import json
                if '{' in accumulated_text and '}' in accumulated_text:
                    start = accumulated_text.find('{')
                    end = accumulated_text.rfind('}') + 1
                    json_str = accumulated_text[start:end]
                    result = json.loads(json_str)
                    intent = result.get("intent", INTENT_AMBIGUOUS)
                    managed_learning_goal = result.get("learning_goal", "").strip()
                    reasoning = result.get("reasoning", "")
                else:
                    intent = INTENT_AMBIGUOUS
                    reasoning = "无法解析 JSON 输出"
            except Exception as parse_err:
                intent = INTENT_AMBIGUOUS
                reasoning = f"JSON 解析失败: {str(parse_err)}"

        logger.info(f"  [主控智能体] 意图识别结果: {intent}")
        if managed_learning_goal:
            logger.info(f"  [主控智能体] 智能管理的 learning_goal: {managed_learning_goal}")
        if reasoning:
            logger.info(f"  [主控智能体] 推理过程: {reasoning}")

        # 记录 token 消耗（流式可能提前终止，需补录估算值）
        user_id = state.get("user_id", 0)
        task_id = state.get("task_id")
        if not llm.get_usage_records():
            input_est = sum(llm._estimate_tokens(m.get("content", "")) for m in messages)
            llm.add_usage(input_tokens=input_est, output_tokens=llm._estimate_tokens(accumulated_text))
        record_from_mimo(llm, user_id, "intent_recognition", task_id)

    except Exception as e:
        intent = INTENT_AMBIGUOUS
        reasoning = f"意图解析异常: {str(e)}"
        managed_learning_goal = None
        logger.error(f"  [主控智能体] 意图识别失败: {str(e)}")

    # 确定下一个节点
    next_node = _route_by_intent(intent, state)
    logger.info(f"  [主控智能体] 路由决策: {intent} -> {next_node}")

    # learning_goal 智能管理：优先采用 LLM 的判定，降级回退到 checkpoint goal
    resolved_learning_goal = None
    current_goal = state.get("learning_goal", "")
    checkpoint_goal = state.get("_checkpoint_learning_goal", "")

    if managed_learning_goal and len(managed_learning_goal) >= 2:
        # LLM 成功输出了管理后的目标
        if managed_learning_goal != current_goal:
            resolved_learning_goal = managed_learning_goal
            logger.info(f"  [主控智能体] LLM 智能管理目标: '{current_goal[:40]}' → '{managed_learning_goal[:80]}'")
    elif intent != INTENT_GENERATE_RESOURCE and checkpoint_goal:
        # 降级方案：LLM 未输出有效目标，但意图非 generate_resource，恢复历史目标
        resolved_learning_goal = checkpoint_goal
        logger.info(f"  [主控智能体] 降级恢复历史目标: {checkpoint_goal[:80]}")

    # 持久化到数据库（按 session_id 区分，保留演进历史）
    final_goal = resolved_learning_goal or current_goal
    plan_id = state.get("plan_id")
    session_id = state.get("session_id")
    if final_goal and plan_id and session_id and final_goal != checkpoint_goal:
        action = _classify_goal_action(checkpoint_goal, final_goal)
        _persist_goal_async(
            plan_id=plan_id,
            session_id=session_id,
            goal=final_goal,
            action=action,
            reasoning=reasoning[:300] if reasoning else "",
        )

    logger.info(f"  [主控智能体] 处理完成")

    result = {
        "intent": intent,
        "next_node": next_node,
        "current_step": f"主控智能体: 意图=[{intent}], 目标=[{(resolved_learning_goal or current_goal)[:40]}], {reasoning[:80]}",
        "iteration_count": iteration + 1,
    }
    if resolved_learning_goal:
        result["learning_goal"] = resolved_learning_goal
    return result


def _route_by_intent(intent: str, state: AgentState) -> str:
    """根据意图决定下一个节点"""
    has_task_breakdown = state.get("task_breakdown") is not None
    needs_confirm = state.get("needs_human_confirm", False)

    # 如果需要用户确认且用户已给出反馈
    if needs_confirm and state.get("human_feedback"):
        if has_task_breakdown:
            logger.info(f"  [主控路由] 已有任务分解 + 用户反馈 -> RAG检索")
            return NODE_RAG_RETRIEVER
        logger.info(f"  [主控路由] 无任务分解 + 用户反馈 -> 任务分解")
        return NODE_TASK_DECOMPOSER

    if intent == INTENT_GENERATE_RESOURCE:
        if has_task_breakdown and state.get("task_breakdown_confirmed"):
            logger.info(f"  [主控路由] 已确认分解 -> RAG检索")
            return NODE_RAG_RETRIEVER
        logger.info(f"  [主控路由] 需要任务分解 -> 任务分解智能体")
        return NODE_TASK_DECOMPOSER

    elif intent == INTENT_SIMPLE_QA:
        logger.info(f"  [主控路由] 简单问答 -> 简答智能体")
        return NODE_SIMPLE_ANSWER

    elif intent == INTENT_GENERATE_QUIZ:
        logger.info(f"  [主控路由] 生成题目 -> 题目生成智能体")
        return NODE_QUIZ_GENERATOR

    elif intent == "generate_type_resource":
        logger.info(f"  [主控路由] 生成类型资源 -> 类型资源生成智能体")
        return NODE_RESOURCE_TYPE_GENERATOR

    elif intent == INTENT_GRADE_QUIZ:
        logger.info(f"  [主控路由] 批改题目 -> 题目判定智能体")
        return NODE_QUIZ_GRADER

    elif intent == INTENT_FOLLOW_UP:
        if has_task_breakdown and not state.get("task_breakdown_confirmed"):
            if state.get("human_feedback"):
                logger.info(f"  [主控路由] 跟随 + 未确认分解 + 有待处理反馈 -> 任务分解智能体")
                return NODE_TASK_DECOMPOSER
            else:
                logger.info(f"  [主控路由] 跟随 + 未确认分解 + 反馈已处理 -> 用户确认")
                return NODE_HUMAN_CONFIRM
        if needs_confirm:
            logger.info(f"  [主控路由] 跟随 + 需确认 -> RAG检索")
            return NODE_RAG_RETRIEVER
        logger.info(f"  [主控路由] 跟随 -> 简答智能体")
        return NODE_SIMPLE_ANSWER

    else:  # ambiguous
        logger.info(f"  [主控路由] 意图模糊 -> 简答智能体")
        return NODE_SIMPLE_ANSWER
