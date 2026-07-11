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
    NODE_HUMAN_CONFIRM, NODE_KB_CONFIRM, NODE_WAIT_USER_REPLY,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP,
    INTENT_CANCEL,
)
from app.agents.llm_factory import get_controller_llm
from app.prompts import CONTROLLER_REACT_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.services.db.java_client import java_client
from app.utils import stream_registry
import json

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

    # 实时推送辅助：全程复用
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))
    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "主控智能体", "content": content}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_start(agent: str, prefix: str = ""):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_start", "agent": agent, "content": prefix}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_chunk(chunk: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_chunk", "content": chunk}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    _emit_thinking("正在分析你的需求...")

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
    asked_profile_question = state.get("_asked_profile_question", "")
    pending_question = state.get("_pending_question", False)

    # 上下文增强：告知主控当前状态
    context_info = ""
    current_module_title = state.get("current_module_title")
    if current_module_title:
        context_info += f"\n[当前前端已选择的模块/资源标题] {current_module_title}"
    source_resource_content = state.get("source_resource_content")
    if source_resource_content:
        context_info += f"\n[系统状态] 已提取到当前选择资源的全文正文，长度: {len(source_resource_content)} 字符"
    if checkpoint_goal:
        context_info += f"\n[上一轮 learning_goal] {checkpoint_goal}"
    if has_task_breakdown:
        context_info += "\n[系统状态] 当前已有任务分解结果，等待用户确认或补充。"
    if has_rag_results:
        context_info += "\n[系统状态] 当前已有 RAG 检索结果。"
    if needs_confirm and state.get("human_feedback"):
        context_info += "\n[系统状态] 用户已给出确认/补充反馈。"
    if asked_profile_question:
        context_info += f"\n[系统状态] 上一轮简答智能体询问了用户关于「{asked_profile_question}」的画像问题，用户当前输入很可能是回答，应归类为 simple_qa 而非生成资源。"
    elif pending_question:
        context_info += f"\n[系统状态] 上一轮系统向用户提出了追问：「{pending_question[:100]}」。用户当前输入很可能是对该问题的回答。如果用户提供了具体的学习主题、知识点或补充信息，你应该根据其内容识别为对应的生成意图（如 generate_resource / generate_quiz 等），否则归类为 simple_qa。"

    if context_info:
        logger.info(f"  [主控智能体] 系统状态: {context_info.strip()}")

    # ==================== ReAct 思考与工具调用循环 ====================
    MAX_REACT_ROUNDS = 6
    react_history = []

    # 工具中文名映射
    TOOL_NAME_MAP = {
        "get_resource_content": "获取资源内容",
        "get_plan_modules": "获取计划模块列表",
        "get_user_profile_fields": "获取用户画像",
        "get_user_quiz_stats": "获取答题统计",
        "get_knowledge_base_docs": "查询知识库文档",
    }

    intent = INTENT_AMBIGUOUS
    reasoning = ""
    managed_learning_goal = None
    resource_type = None
    kb_relevant = True  # 默认知识库有相关资料
    new_events = []

    # 语言指令触发时，主控通过工具查询到的模块详情（用于更新状态）
    fetched_module_id = None
    fetched_module_title = None
    fetched_module_content = None

    for round_num in range(1, MAX_REACT_ROUNDS + 1):
        logger.info(f"  [主控智能体] ReAct - 第 {round_num} 轮")

        react_context = ""
        if react_history:
            react_context = "\n\n## 工具调用记录\n" + "\n".join(react_history)

        # 准备 prompt
        messages = [
            {"role": "system", "content": CONTROLLER_REACT_PROMPT.format(max_rounds=MAX_REACT_ROUNDS)},
            {"role": "user", "content": f"对话历史:\n{history_text}\n{context_info}\n\n当前用户输入: {user_message}{react_context}\n\n请进行决策，输出 JSON:"}
        ]

        try:
            # 流式推送 thought 字段，逐 token 到前端
            _chunk_emitted = False
            def _on_thought_chunk(chunk: str):
                nonlocal _chunk_emitted
                _chunk_emitted = True
                _emit_thinking_chunk(chunk)

            _emit_thinking_start("主控智能体", "思考: ")
            react_result = llm.chat_json_stream(messages, on_chunk=_on_thought_chunk, stream_field="thought")
            record_from_mimo(llm, state.get("user_id", 0), "controller_react", state.get("task_id"))

            if not isinstance(react_result, dict):
                logger.warning(f"  [主控智能体] 返回非字典类型，终止 ReAct")
                break

            thought = react_result.get("thought", "")
            decision = react_result.get("decision", "finish").lower().strip()

            # 降级：如果流式未触发（如 JSON 解析重试走了非流式路径），补推完整 thought
            if not _chunk_emitted and thought:
                _emit_thinking_chunk(thought)

            logger.info(f"  [主控智能体] 思考: {thought[:100]}...")

            if decision == "tool_call":
                actions = react_result.get("actions", [])
                logger.info(f"  [主控智能体] 决定调用工具: {len(actions)} 个动作")

                # thought 已通过流式推送，这里不再重复推送

                for act in actions:
                    act_name = act.get("action")
                    tool_cn_name = TOOL_NAME_MAP.get(act_name, act_name)
                    logger.info(f"    - 执行工具: {act_name}")

                    # 推送工具调用开始
                    _emit_thinking(f"调用工具: {tool_cn_name}")

                    if act_name == "get_resource_content":
                        rid = act.get("resource_id") or act.get("resourceId")
                        try:
                            res = java_client.get_resource_by_id(int(rid))
                            
                            # 提取正文内容并缓存
                            md = res.get("moduleData")
                            if isinstance(md, str) and md:
                                try:
                                    md = json.loads(md)
                                except Exception:
                                    md = {}
                            content = ""
                            if isinstance(md, dict):
                                content = md.get("content") or md.get("html") or ""
                            if not content:
                                content = res.get("title", "")
                                
                            fetched_module_id = int(rid)
                            fetched_module_title = res.get("title") or "未知"
                            fetched_module_content = content

                            react_history.append(f"工具 get_resource_content(id={rid}) 结果: 标题={fetched_module_title}, 内容片段={content[:2000]}...")
                            # 推送结果概述
                            _emit_thinking(f"{tool_cn_name}完成: 获取到资源「{fetched_module_title}」，内容长度{len(content)}字")
                        except Exception as e:
                            react_history.append(f"工具 get_resource_content 失败: {e}")
                            _emit_thinking(f"{tool_cn_name}失败: {e}")

                    elif act_name == "get_plan_modules":
                        try:
                            mods = java_client.get_plan_resources(state.get("plan_id", 0))
                            # 从 moduleData JSON 中提取标题（顶层 title 字段通常为空）
                            def _extract_title(m):
                                t = m.get('title')
                                if t:
                                    return t
                                try:
                                    md = m.get('moduleData', '')
                                    if isinstance(md, str) and md:
                                        obj = json.loads(md)
                                        if isinstance(obj, dict):
                                            return obj.get('title')
                                except Exception:
                                    pass
                                return f"模块{m.get('order') or m.get('moduleOrder') or '?'}"
                            summary = [f"ID:{m['id']}, Type:{m.get('moduleType')}, Title:{_extract_title(m)}" for m in mods]
                            react_history.append(f"工具 get_plan_modules 结果: \n" + "\n".join(summary))
                            # 推送结果概述
                            titles = [_extract_title(m) or f"模块{m.get('moduleOrder', '?')}" for m in mods[:5]]
                            _emit_thinking(f"{tool_cn_name}完成: 共{len(mods)}个资源 - {', '.join(titles)}")
                        except Exception as e:
                            react_history.append(f"工具 get_plan_modules 失败: {e}")
                            _emit_thinking(f"{tool_cn_name}失败: {e}")

                    elif act_name == "get_user_profile_fields":
                        fields = act.get("fields", [])
                        try:
                            prof = java_client.get_user_profile(state.get("user_id", 0))
                            lb = prof.get("learning_behavior", {})
                            extracted = {k: lb.get(k) for k in fields if k in lb}
                            react_history.append(f"工具 get_user_profile_fields 结果: {json.dumps(extracted, ensure_ascii=False)}")
                            # 推送结果概述
                            field_count = len(extracted)
                            _emit_thinking(f"{tool_cn_name}完成: 获取到{field_count}个画像字段 - {', '.join(extracted.keys())}")
                        except Exception as e:
                            react_history.append(f"工具 get_user_profile_fields 失败: {e}")
                            _emit_thinking(f"{tool_cn_name}失败: {e}")

                    elif act_name == "get_user_quiz_stats":
                        try:
                            stats = java_client.get_user_quiz_stats(state.get("user_id", 0), state.get("plan_id", 0))
                            react_history.append(f"工具 get_user_quiz_stats 结果: {json.dumps(stats, ensure_ascii=False)}")
                            # 推送结果概述
                            accuracy = stats.get("accuracy", "未知")
                            total = stats.get("total_questions", 0)
                            _emit_thinking(f"{tool_cn_name}完成: 共答题{total}道，正确率{accuracy}")
                        except Exception as e:
                            react_history.append(f"工具 get_user_quiz_stats 失败: {e}")
                            _emit_thinking(f"{tool_cn_name}失败: {e}")

                    elif act_name == "get_knowledge_base_docs":
                        try:
                            docs = java_client.get_indexed_kb_documents()
                            doc_summary = []
                            for d in docs:
                                doc_summary.append(f"- {d.get('docName', '未知')} (chunks={d.get('chunkCount', 0)})")
                            docs_text = "\n".join(doc_summary) if doc_summary else "（暂无已入库文档）"
                            react_history.append(f"工具 get_knowledge_base_docs 结果: 共{len(docs)}个已入库文档:\n{docs_text}")
                            _emit_thinking(f"{tool_cn_name}完成: 知识库中共{len(docs)}个已入库文档")
                        except Exception as e:
                            react_history.append(f"工具 get_knowledge_base_docs 失败: {e}")
                            _emit_thinking(f"{tool_cn_name}失败: {e}")

                # stream_events 仍保留（已被 resource_chat.py 过滤掉 thinking，不会重复推送）
                new_events.append({
                    "event_type": "thinking",
                    "agent": "controller",
                    "data": {"message": f"思考: {thought}\n决定使用工具..."},
                    "step_description": "思考并收集信息"
                })

                continue

            else:
                # finish
                intent = react_result.get("intent", INTENT_AMBIGUOUS)
                managed_learning_goal = str(react_result.get("learning_goal", "")).strip()
                reasoning = react_result.get("reasoning", "")
                resource_type = react_result.get("resource_type")
                kb_relevant = react_result.get("kb_relevant", True)
                logger.info(f"  [主控智能体] ReAct 结束，最终意图: {intent}, KB相关: {kb_relevant}")
                # 推送最终决策
                _emit_thinking(f"决策完成: 意图={intent}，目标={managed_learning_goal or '未明确'}")
                break

        except Exception as e:
            logger.error(f"  [主控智能体] ReAct 异常: {e}")
            break

    # 确定下一个节点
    
    # 【空载拦截】：如果用户想生成动画、播客、类型资源或题目，但上下文中没有任何资源，强行拦截转为追问
    has_source_content = bool(state.get("source_resource_content") or fetched_module_content)
    if intent in ["generate_type_resource", "generate_animation", INTENT_GENERATE_QUIZ] and not has_source_content:
        logger.info(f"  [主控智能体] 空载拦截：缺少源文本，将 {intent} 强行转为追问")
        intent = "clarify"
        reasoning = "用户请求生成动画、导图、播客、题目等特定类型资源，但在当前的对话上下文中，由于没有明确挂载之前的资源文本，系统处于'空载'状态。请委婉地询问用户：具体想要基于哪个知识点或刚刚学过的哪个主题来生成？并建议用户先选择一个具体的模块资源。"

    # 【知识库相关性检查】：如果主控判断知识库无相关资料，路由到知识库确认节点
    # 已确认使用网络资源时跳过，避免循环触发
    if intent == INTENT_GENERATE_RESOURCE and not kb_relevant and not state.get("web_search_fallback"):
        logger.info(f"  [主控智能体] 知识库无相关资料，路由到知识库确认节点")
        # 用 LLM 生成的 reasoning 作为面向用户的个性化提示
        kb_message = reasoning or "知识库中暂无与该主题直接相关的资料，生成内容将主要参考网络资源。是否继续？"
        # 流式推送确认消息（逐 token 打出，给用户阅读感）
        _emit_thinking_start("主控智能体", "提示: ")
        _emit_thinking_chunk(kb_message)
        # 发送确认事件（触发前端按钮）
        new_events.append({
            "event_type": "confirm_needed",
            "data": {
                "message": kb_message,
                "confirmation_type": "kb_check",
            },
        })
        return {
            "intent": intent,
            "next_node": NODE_KB_CONFIRM,
            "needs_human_confirm": True,
            "learning_goal": managed_learning_goal or state.get("learning_goal", ""),
            "kb_check_message": kb_message,
            "reasoning": reasoning,
            "current_step": "主控智能体: 知识库无相关资料，等待用户确认是否使用网络资源",
            "iteration_count": iteration + 1,
            "stream_events": new_events,
        }

    next_node = _route_by_intent(intent, state)

    if intent == "clarify":
        # 直接追问并通过 NODE_WAIT_USER_REPLY checkpoint 暂停，等待用户回答后恢复图
        question = reasoning or "请补充说明你具体想学习哪方面内容？"
        logger.info(f"  [主控智能体] 决定追问并进入 checkpoint 暂停: {question[:80]}")
        try:
            _emit_thinking_start("主控智能体", "追问: ")
            _emit_thinking_chunk(question)
            if _sse_cb:
                _sse_cb(f'data: {json.dumps({"type": "chunk", "content": question}, ensure_ascii=False)}\n\n')
        except Exception:
            pass
        return {
            "intent": "clarify",
            "next_node": NODE_WAIT_USER_REPLY,
            "_pending_question": question,
            "needs_human_confirm": True,
            "current_step": "主控智能体决定追问澄清，等待用户回复",
            "iteration_count": iteration + 1,
            "stream_events": [
                {"event_type": "content", "agent": "controller", "data": {"text": question}},
                {"event_type": "thinking", "agent": "controller", "data": {"message": f"需要澄清需求: {question[:20]}..."}, "step_description": "准备向用户追问"},
            ],
        }
        
    logger.info(f"  [主控智能体] 路由决策: {intent} -> {next_node}")

    # learning_goal 智能管理：优先采用 LLM 的判定，降级回退到 checkpoint goal
    resolved_learning_goal = None
    current_goal = state.get("learning_goal", "")
    checkpoint_goal = state.get("_checkpoint_learning_goal", "")
    current_module_title = fetched_module_title if fetched_module_title else state.get("current_module_title")

    if intent in [INTENT_GENERATE_QUIZ, "generate_type_resource", "generate_animation"] and current_module_title:
        # 针对具体模块的资源/题目生成，核心学习目标应限定为该模块的标题
        resolved_learning_goal = current_module_title
        logger.info(f"  [主控智能体] 模块特异性生成，自动重置目标为模块标题: '{current_module_title}'")
    elif managed_learning_goal and len(managed_learning_goal) >= 2:
        if managed_learning_goal != current_goal:
            resolved_learning_goal = managed_learning_goal
            logger.info(f"  [主控智能体] LLM 智能管理目标: '{current_goal[:40]}' → '{managed_learning_goal[:80]}'")
    elif intent not in [INTENT_GENERATE_RESOURCE, "generate_type_resource", "generate_animation"] and checkpoint_goal:
        # 降级方案：恢复历史目标
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

    final_goal = resolved_learning_goal or current_goal
    result = {
        "intent": intent,
        "next_node": next_node,
        "current_step": f"主控智能体: 意图=[{intent}], 目标=[{final_goal[:40]}], {reasoning[:80]}",
        "iteration_count": iteration + 1,
        "stream_events": new_events,
        "_pending_question": False,          # 消费完毕后清除，防止状态污染
        "_asked_profile_question": "",       # 消费完毕后清除，防止状态污染
    }
    if fetched_module_id is not None:
        result["current_module_id"] = fetched_module_id
        result["current_module_title"] = fetched_module_title
        result["source_resource_content"] = fetched_module_content
    
    if resource_type:
        result["resource_type"] = resource_type
        
    if intent == "confirm":
        result["task_breakdown_confirmed"] = True
        result["human_feedback"] = None
    if intent == "simple_qa" or intent == "clarify" or intent == INTENT_CANCEL:
        result["task_breakdown"] = None
        result["task_breakdown_confirmed"] = False
        result["needs_human_confirm"] = False
        result["human_feedback"] = None
        # 用户取消确认 → 计划状态从"待确认(2)"回退到"学习中(3)"
        if intent == INTENT_CANCEL and state.get("plan_id"):
            try:
                java_client.update_plan_status(state["plan_id"], 3)
            except Exception:
                pass
        
    # 自动伪造 task_breakdown 以便下游生成补充资源
    if intent in ["generate_type_resource", "generate_animation"]:
        current_module_id = fetched_module_id if fetched_module_id is not None else state.get("current_module_id")
        if current_module_id and not state.get("task_breakdown"):
            current_title = fetched_module_title if fetched_module_title else (state.get("current_module_title") or "当前学习模块")
            logger.info(f"  [主控智能体] 自动伪造 task_breakdown (module_id={current_module_id}, resource_type={resource_type})")

            # 确定资源类型
            res_type = resource_type
            if intent == "generate_animation":
                res_type = "animation"
            elif not res_type:
                # 从用户消息中推断资源类型
                user_msg = state.get("user_message", "").lower()
                if "思维导图" in user_msg or "mindmap" in user_msg or "导图" in user_msg:
                    res_type = "mindmap"
                elif "播客" in user_msg or "podcast" in user_msg:
                    res_type = "podcast"
                elif "总结" in user_msg or "summary" in user_msg:
                    res_type = "summary"
                elif "代码" in user_msg or "code" in user_msg:
                    res_type = "code"
                elif "ppt" in user_msg:
                    res_type = "pptx"
                else:
                    res_type = "text"
                logger.info(f"  [主控智能体] LLM 未返回 resource_type，从用户消息推断: {res_type}")

            # 获取当前资源的 moduleOrder，新资源应该在同一个模块下
            current_module_order = state.get("current_module_order", 0)

            result["task_breakdown"] = {
                "title": current_title,
                "modules": [{
                    "module_order": current_module_order,
                    "title": current_title,
                    "description": "用户请求的补充学习资源",
                    "resources": [{
                        "resource_type": res_type,
                        "title": f"{current_title}的{res_type}资源"
                    }]
                }]
            }
            result["task_breakdown_confirmed"] = True

    if resolved_learning_goal:
        result["learning_goal"] = resolved_learning_goal
    result["_checkpoint_learning_goal"] = final_goal
    return result


def _route_by_intent(intent: str, state: AgentState) -> str:
    """根据意图决定下一个节点"""
    has_task_breakdown = state.get("task_breakdown") is not None
    needs_confirm = state.get("needs_human_confirm", False)

    if intent == "confirm":
        logger.info(f"  [主控路由] LLM 识别为用户确认 -> RAG 检索")
        return NODE_RAG_RETRIEVER

    elif intent == INTENT_GENERATE_RESOURCE:
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
        
    elif intent == "generate_animation":
        logger.info(f"  [主控路由] 生成动画 -> 动画生成智能体")
        return NODE_ANIMATION_SKILL_GENERATOR

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

    elif intent == INTENT_CANCEL:
        logger.info(f"  [主控路由] 用户取消 -> 简答智能体")
        return NODE_SIMPLE_ANSWER

    else:  # ambiguous
        logger.info(f"  [主控路由] 意图模糊 -> 简答智能体")
        return NODE_SIMPLE_ANSWER
