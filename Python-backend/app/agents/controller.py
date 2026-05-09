"""
主控智能体 - 负责意图识别和任务调度
在不同情况下调度不同智能体，控制整个进度和流程
"""
import logging
from typing import Dict, Any
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
1. **generate_resource** - 用户明确要求生成学习资源、学习材料、学习计划，或要学习某个主题
2. **simple_qa** - 用户只是简短提问、闲聊、打招呼，或不需要生成学习资源的简单问答
3. **generate_quiz** - 用户要求生成题目、练习题、测试题、模拟考试等
4. **grade_quiz** - 用户提交了答案要求批改、评分、判断对错
5. **follow_up** - 用户对之前的内容进行追问、补充说明、要求修改，或者回复确认/否定
6. **ambiguous** - 用户意图不明确，需要进一步询问

## 判断规则
- 如果用户说"学习XX"、"帮我生成XX的学习资料"、"创建学习计划" -> generate_resource
- 如果用户问了一个简单知识点问题、打招呼、或不需要资源生成 -> simple_qa
- 如果用户说"出几道题"、"给我出题"、"测试一下" -> generate_quiz
- 如果用户提交了答案要求批改 -> grade_quiz
- 如果用户在已有对话基础上补充说明、确认或否定之前的方案 -> follow_up
- 如果无法判断意图 -> ambiguous

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
        logger.info(f"  [主控智能体] 正在调用 LLM 进行意图识别...")
        result = llm.chat_json(messages, temperature=0.2)
        intent = result.get("intent", INTENT_AMBIGUOUS)
        reasoning = result.get("reasoning", "")
        logger.info(f"  [主控智能体] 意图识别结果: {intent}")
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
            logger.info(f"  [主控路由] 跟随 + 未确认分解 -> 任务分解智能体")
            return NODE_TASK_DECOMPOSER
        if needs_confirm:
            logger.info(f"  [主控路由] 跟随 + 需确认 -> RAG检索")
            return NODE_RAG_RETRIEVER
        logger.info(f"  [主控路由] 跟随 -> 简答智能体")
        return NODE_SIMPLE_ANSWER

    else:  # ambiguous
        logger.info(f"  [主控路由] 意图模糊 -> 简答智能体")
        return NODE_SIMPLE_ANSWER
