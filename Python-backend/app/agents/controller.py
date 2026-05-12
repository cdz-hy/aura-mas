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
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_module_ids:
        # 检查重试次数限制
        if retry_count >= max_retries:
            logger.warning(f"  [主控智能体] 已达到最大重试次数 ({max_retries})，放弃重试")
            logger.warning(f"  [主控智能体] 未通过模块: {retry_module_ids}")
            return {
                "intent": "retry_failed",
                "next_node": END,  # 直接结束（画像维护改为异步后台执行）
                "current_step": f"已达到最大重试次数，放弃重试模块 {retry_module_ids}",
                "retry_module_ids": [],  # 清除重试标记
                "retry_mode": False,
                "iteration_count": iteration + 1,
            }
        
        logger.info(f"  [主控智能体] 检测到需要重试的模块: {retry_module_ids}")
        logger.info(f"  [主控智能体] 当前重试次数: {retry_count}/{max_retries}")
        logger.info(f"  [主控智能体] 只重新生成这些模块，保留其他模块")
        
        # 设置重试模式，让 RAG 和编排智能体只处理这些模块
        return {
            "intent": "retry_modules",
            "next_node": NODE_RAG_RETRIEVER,
            "retry_mode": True,
            "target_module_ids": retry_module_ids,
            "retry_count": retry_count + 1,
            "current_step": f"主控智能体: 模块级别重试 (第 {retry_count + 1} 次)，重新生成模块 {retry_module_ids}",
            "iteration_count": iteration + 1,
        }

    # 快速路径：如果前端已确认任务分解，直接进入 RAG 检索，无需 LLM 分类
    # 但如果初始状态已指定 intent（如 generate_quiz），按指定意图路由
    preset_intent = state.get("intent", "")
    if state.get("task_breakdown_confirmed") and state.get("task_breakdown"):
        if preset_intent == INTENT_GENERATE_QUIZ:
            logger.info(f"  [主控智能体] 预设意图: generate_quiz，路由 -> 题目生成智能体")
            return {
                "intent": INTENT_GENERATE_QUIZ,
                "next_node": NODE_QUIZ_GENERATOR,
                "current_step": "预设意图: 生成题目",
                "iteration_count": iteration + 1,
            }
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
