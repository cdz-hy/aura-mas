"""
主控智能体 - 负责意图识别和任务调度
在不同情况下调度不同智能体，控制整个进度和流程
"""
import logging
from typing import Dict, Any
from langgraph.graph import END
from app.agents.schemas import (
    AgentState, NODE_CONTROLLER, NODE_TASK_DECOMPOSER, NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER, NODE_QUIZ_GENERATOR, NODE_QUIZ_GRADER,
    NODE_RESOURCE_GENERATOR, NODE_HUMAN_CONFIRM,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP,
)
from app.agents.llm_factory import get_controller_llm

logger = logging.getLogger("agents.controller")

SYSTEM_PROMPT = """你是一个多智能体学习系统的主控调度器。你的职责是准确识别用户意图并决定下一步操作。

## 可用意图类型
1. **generate_resource** - 用户想了解、学习、掌握某个知识/概念/技术，需要生成结构化学习资料
2. **simple_qa** - 闲聊、打招呼、日常对话、或答案极简短的事实性问答（不需学习资料）
3. **generate_quiz** - 用户要求生成题目、练习题、测试题、模拟考试等
4. **grade_quiz** - 用户提交了答案要求批改、评分、判断对错
5. **follow_up** - 用户对之前的内容进行追问、补充说明、要求修改，或回复确认/否定
6. **ambiguous** - 用户意图不明确，需要进一步询问

## 判断规则 (核心)

### generate_resource（生成学习资料）
以下情况应归类为 generate_resource，因为用户需要的是结构化的学习内容而非简单的问答：
- "学习XX"、"了解XX"、"XX是什么"、"XX的原理"、"XX的过程"
- "我想知道XX"、"我想了解XX"、"XX相关知识点"
- "XX怎么工作"、"XX的实现"、"XX的概念"
- "帮我生成XX"、"给我讲讲XX"
- 任何涉及知识/技术/学科领域的查询，即使语气上像提问

### simple_qa（简答）
以下情况才归类为 simple_qa，因为不需要生成学习资料：
- 打招呼："你好"、"嗨"
- 闲聊："今天心情好"、"谢谢"
- 极简短的事实问答："1+1等于几"、"现在几点了"
- 系统操作类："你能做什么"、"怎么用"
- 注意：涉及知识学习的问题 NOT simple_qa

### 其他意图
- generate_quiz：用户说"出几道题"、"测试一下"、"给我出题"
- grade_quiz：用户提交了答案要求批改
- follow_up：在已有对话基础上补充说明、确认或否定
- ambiguous：完全无法判断意图

## 输出格式
严格输出 JSON，不要输出其他内容：
{"intent": "意图类型", "reasoning": "简要推理过程"}"""


def controller_node(state: AgentState) -> Dict[str, Any]:
    """主控智能体节点 - 意图识别与路由"""
    user_message = state.get("user_message", "")
    iteration = state.get("iteration_count", 0)

    logger.info(f"{'='*60}")
    logger.info(f"  [主控智能体] 开始处理 (迭代: {iteration})")
    logger.info(f"  用户输入: {user_message[:100]}")
    logger.info(f"{'='*60}")

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
    if state.get("task_breakdown_confirmed") and state.get("task_breakdown"):
        logger.info(f"  [主控智能体] 任务分解已确认，快速路由 -> RAG 检索")
        return {
            "intent": INTENT_GENERATE_RESOURCE,
            "next_node": NODE_RAG_RETRIEVER,
            "current_step": "任务分解已确认，开始检索学习资源",
            "iteration_count": iteration + 1,
        }

    llm = get_controller_llm()

    # 构造对话上下文
    history_text = ""
    chat_history = state.get("chat_history", [])
    if chat_history:
        recent = chat_history[-10:]  # 最近10轮
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            history_text += f"{role}: {msg['content']}\n"
        logger.info(f"  [主控智能体] 对话历史: {len(chat_history)} 轮 (使用最近 {len(recent)} 轮)")

    has_task_breakdown = state.get("task_breakdown") is not None
    has_rag_results = bool(state.get("rag_results"))
    needs_confirm = state.get("needs_human_confirm", False)

    # 上下文增强：告知主控当前状态
    context_info = ""
    if has_task_breakdown:
        context_info += "\n[系统状态] 当前已有任务分解结果，等待用户确认或补充。"
    if has_rag_results:
        context_info += "\n[系统状态] 当前已有 RAG 检索结果。"
    if needs_confirm and state.get("human_feedback"):
        context_info += "\n[系统状态] 用户已给出确认/补充反馈。"

    if context_info:
        logger.info(f"  [主控智能体] 系统状态: {context_info.strip()}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"对话历史:\n{history_text}\n{context_info}\n\n当前用户输入: {user_message}\n\n请识别意图并输出 JSON:"}
    ]

    try:
        logger.info(f"  [主控智能体] 正在流式调用 LLM 进行意图识别...")
        
        intent = None
        reasoning = ""
        accumulated_text = ""
        
        # 使用流式输出
        for chunk in llm.chat_stream(messages, temperature=0.2):
            accumulated_text += chunk
            
            # 提前判断：检测关键词快速路由
            # 注意：只用 JSON key 匹配，不用中文短语，避免 LLM 推理文本中的否定句式误匹配
            # 例如 "这不是简单问答" 不应匹配 simple_qa
            if intent is None:
                acc = accumulated_text.lower()

                # generate_resource: JSON 中的 intent 字段值
                if ('"intent":"generate_resource"' in acc
                        or '"intent": "generate_resource"' in acc):
                    intent = INTENT_GENERATE_RESOURCE
                    logger.info(f"  [主控智能体] 流式判断: 检测到资源生成意图，提前路由!")
                    break

                # simple_qa: 只匹配 JSON key，避免 "不是简单问答" 误匹配
                if ('"intent":"simple_qa"' in acc
                        or '"intent": "simple_qa"' in acc):
                    intent = INTENT_SIMPLE_QA
                    logger.info(f"  [主控智能体] 流式判断: 检测到简单问答意图，提前路由!")
                    break

                # generate_quiz
                if ('"intent":"generate_quiz"' in acc
                        or '"intent": "generate_quiz"' in acc):
                    intent = INTENT_GENERATE_QUIZ
                    logger.info(f"  [主控智能体] 流式判断: 检测到题目生成意图，提前路由!")
                    break

                # grade_quiz
                if ('"intent":"grade_quiz"' in acc
                        or '"intent": "grade_quiz"' in acc):
                    intent = INTENT_GRADE_QUIZ
                    logger.info(f"  [主控智能体] 流式判断: 检测到题目判定意图，提前路由!")
                    break

                # follow_up
                if ('"intent":"follow_up"' in acc
                        or '"intent": "follow_up"' in acc):
                    intent = INTENT_FOLLOW_UP
                    logger.info(f"  [主控智能体] 流式判断: 检测到跟随意图，提前路由!")
                    break
        
        # 如果流式判断没有识别出意图，尝试解析完整 JSON
        if intent is None:
            try:
                import json
                # 尝试提取 JSON
                if '{' in accumulated_text and '}' in accumulated_text:
                    start = accumulated_text.find('{')
                    end = accumulated_text.rfind('}') + 1
                    json_str = accumulated_text[start:end]
                    result = json.loads(json_str)
                    intent = result.get("intent", INTENT_AMBIGUOUS)
                    reasoning = result.get("reasoning", "")
                else:
                    intent = INTENT_AMBIGUOUS
                    reasoning = "无法解析意图"
            except:
                intent = INTENT_AMBIGUOUS
                reasoning = "JSON 解析失败"
        
        logger.info(f"  [主控智能体] 意图识别结果: {intent}")
        if reasoning:
            logger.info(f"  [主控智能体] 推理过程: {reasoning}")
            
    except Exception as e:
        intent = INTENT_AMBIGUOUS
        reasoning = f"意图解析异常: {str(e)}"
        logger.error(f"  [主控智能体] 意图识别失败: {str(e)}")

    # 确定下一个节点
    next_node = _route_by_intent(intent, state)
    logger.info(f"  [主控智能体] 路由决策: {intent} -> {next_node}")
    logger.info(f"  [主控智能体] 处理完成")

    return {
        "intent": intent,
        "next_node": next_node,
        "current_step": f"主控智能体: 意图识别为 [{intent}], {reasoning}",
        "iteration_count": iteration + 1,
    }


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
