"""
简答智能体 - 简短回答用户问题，决定是否追问，维护对话上下文
可主动询问学习满意度、学习要求、Felder-Silverman 模型相关问题
"""
import json
import logging
import random
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER
from app.agents.llm_factory import get_simple_answer_llm
from app.prompts import SIMPLE_ANSWER_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.utils.profile_utils import map_dimension_name

logger = logging.getLogger("agents.simple_answer")



PROFILE_QUESTIONS = {
    "sensing_vs_intuitive": [
        "在学习新知识时，你更倾向于通过具体的实例和实验来理解，还是更喜欢先了解抽象的理论和概念框架？",
        "如果让你学习一个新的技术概念，你会更喜欢看一个完整的实际案例演示，还是先阅读理论原理的阐述？",
        "你觉得自己在学习时是更注重细节和事实，还是更善于把握整体的概念和关联？",
    ],
    "visual_vs_verbal": [
        "你学习时更喜欢看图表、流程图、思维导图这类视觉化的内容，还是更喜欢阅读详细的文字说明？",
        "当理解一个复杂概念时，一张好的示意图和一段详细的文字解释，哪个对你帮助更大？",
        "你平时记笔记时更习惯画图示还是写文字？",
    ],
    "active_vs_reflective": [
        "学完一个新知识点后，你更喜欢立刻动手实践尝试，还是先在脑海中反复思考消化？",
        "你更喜欢通过小组讨论来加深理解，还是独自安静地思考？",
        "面对一个新的学习任务，你的第一反应是马上开始动手做，还是先花时间规划和思考？",
    ],
    "sequential_vs_global": [
        "你学习时更喜欢按照逻辑顺序一步一步地深入，还是先了解整体框架再逐步细化？",
        "当面对一个复杂的知识体系时，你更希望先看到完整的知识地图，还是从第一个知识点开始逐步学习？",
        "你是否经常在学到后面的内容时，突然对前面的知识有了更深的理解？",
    ],
    "knowledge_base": [
        "在当前学习的领域中，你之前已经学过哪些相关的课程或知识？",
        "你对这个领域的基础概念了解程度如何？有没有特别熟悉或特别陌生的部分？",
    ],
    "quiz_preference": [
        "你平时做练习题时，更喜欢选择题、填空题还是简答题？",
        "你觉得自己在哪类题型上表现更好？哪类题型需要加强练习？",
    ],
    "content_preference": [
        "在学习资源方面，你更偏好视频讲解、图文教程、流程图，还是代码示例？",
        "你学习时更喜欢看实际案例分析，还是理论知识的系统梳理？",
    ],
}


def simple_answer_node(state: AgentState) -> Dict[str, Any]:
    """简答智能体节点"""
    user_message = state.get("user_message", "")
    chat_history = state.get("chat_history", [])
    user_profile = state.get("user_profile", {})

    logger.info(f"{'='*60}")
    logger.info(f"  [简答智能体] 开始处理")
    logger.info(f"  用户输入: {user_message[:100]}")

    # 检查是否为异常追问模式：智能体发现内容偏离，需要向用户澄清
    is_anomaly_clarify = state.get("anomaly_clarify", False)
    anomaly_reason = state.get("anomaly_reason", "")

    if is_anomaly_clarify and anomaly_reason:
        logger.info(f"  [简答智能体] 异常追问模式: {anomaly_reason}")
        return _generate_anomaly_clarification(state, anomaly_reason, chat_history, user_message)

    llm = get_simple_answer_llm()

    # 构建对话历史文本（包含更多轮次以便 LLM 理解上下文）
    history_text = ""
    recent = chat_history[-20:]  # 最近20轮
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content']}\n"

    # 判断是否应该主动询问画像（低频率触发）
    should_ask_profile = _should_ask_profile(chat_history, user_profile)
    profile_hint = ""

    if should_ask_profile:
        dim, question = _pick_profile_question(user_profile)
        profile_hint = f"\n\n[系统建议] 可以考虑询问用户关于 {dim} 维度的学习风格，参考问题: {question}"
        logger.info(f"  [简答智能体] 建议询问画像: 维度={dim}")

    messages = [
        {"role": "system", "content": SIMPLE_ANSWER_PROMPT},
        {"role": "user", "content": f"""对话历史:
{history_text}

当前用户输入: {user_message}
{profile_hint}

请分析对话上下文，判断是否包含学习风格信息，并输出 JSON:"""}
    ]

    try:
        logger.info(f"  [简答智能体] 正在调用 LLM 生成回复（流式）...")
        sse_cb = state.get("sse_callback")

        def _on_chunk(chunk: str):
            if sse_cb:
                try:
                    sse_cb(f'data: {json.dumps({"type": "stream_text", "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        result = llm.chat_json_stream(messages, on_chunk=_on_chunk, stream_field="response")
        record_from_mimo(llm, state.get("user_id", 0), "simple_qa", state.get("task_id"))
        response = result.get("response", "")
        action = result.get("action", "answer")
        should_update = result.get("should_update_profile", False)
        profile_dimension = result.get("profile_dimension")
        profile_analysis = result.get("profile_analysis")

        logger.info(f"  [简答智能体] 回复类型: {action}")
        logger.info(f"  [简答智能体] 回复内容: {response[:150]}")
        
        if should_update:
            logger.info(f"  [简答智能体] 检测到画像信息!")
            logger.info(f"    维度: {profile_dimension}")
            logger.info(f"    分析: {profile_analysis}")
        
        logger.info(f"{'='*60}")

        events = [{
            "event_type": "content",
            "agent": "simple_answer",
            "data": {"text": response, "action": action},
            "step_description": "简答智能体回复"
        }]

        return_data = {
            "stream_events": events,
            "current_step": f"简答智能体: {action}",
        }

        # 更新对话历史
        new_history = list(chat_history)
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": response})
        return_data["chat_history"] = new_history

        # 如果检测到画像信息，标记需要更新
        if should_update and profile_dimension:
            # 映射维度名称到标准字段名
            mapped_dimension = map_dimension_name(profile_dimension)
            
            return_data["profile_update_needed"] = True
            return_data["stream_events"].append({
                "event_type": "profile_update",
                "agent": "simple_answer",
                "data": {
                    "dimension": mapped_dimension,
                    "answer": user_message,
                    "analysis": profile_analysis,
                },
                "step_description": f"检测到画像信息: {mapped_dimension}"
            })

        return return_data

    except Exception as e:
        logger.error(f"  [简答智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "stream_events": [{
                "event_type": "content",
                "agent": "simple_answer",
                "data": {"text": "抱歉，我暂时无法回答这个问题，请稍后再试。", "action": "answer"},
                "step_description": "简答智能体回复（降级）"
            }],
            "current_step": f"简答智能体: 生成异常 - {str(e)}",
        }


ANOMALY_CLARIFY_PROMPT = """你是一个友好的 AI 学习助手。系统在处理用户请求时发现了一些问题，需要你向用户追问澄清。

## 背景
上一轮智能体处理时，检测到以下问题：{anomaly_reason}

用户的原始请求是：{user_message}

## 你的任务
1. 用友好、自然的语气告诉用户遇到了什么问题（用自己的话简要说明，不要照搬系统术语）
2. 向用户追问，帮助澄清 TA 的真实需求
3. 给出 1-2 个具体的澄清方向或建议

## 规则
- 语气友好自然，不要让用户觉得是"系统出错了"
- 保持专业但亲切
- 严禁使用 emoji
- 使用中文回复
- 回复控制在 3-5 句话

严格输出 JSON：
{{
  "action": "clarify",
  "response": "你的追问文本"
}}"""


def _generate_anomaly_clarification(
    state: AgentState,
    anomaly_reason: str,
    chat_history: list,
    user_message: str,
) -> Dict[str, Any]:
    """生成异常追问澄清的回复"""
    llm = get_simple_answer_llm()

    history_text = ""
    recent = chat_history[-10:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content']}\n"

    prompt = ANOMALY_CLARIFY_PROMPT.format(
        anomaly_reason=anomaly_reason,
        user_message=user_message,
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"对话历史:\n{history_text}\n\n请生成追问澄清的回复，输出 JSON:"},
    ]

    try:
        result = llm.chat_json(messages, max_tokens=512)
        from app.utils.token_recorder import record_from_mimo
        record_from_mimo(llm, state.get("user_id", 0), "anomaly_clarify", state.get("task_id"))
        response = result.get("response", f"抱歉，我在处理你的请求时遇到了一些困惑。能否请你再详细说明一下你的需求？")

        logger.info(f"  [简答智能体] 异常追问: {response[:150]}")
        logger.info(f"{'='*60}")

        new_history = list(chat_history)
        new_history.append({"role": "assistant", "content": response})

        return {
            "anomaly_clarify": False,  # 清除异常追问标记
            "anomaly_reason": "",
            "chat_history": new_history,
            "current_step": "简答智能体: 异常追问澄清",
            "stream_events": [{
                "event_type": "content",
                "agent": "simple_answer",
                "data": {"text": response, "action": "clarify"},
                "step_description": "异常追问澄清"
            }],
        }
    except Exception as e:
        logger.error(f"  [简答智能体] 异常追问生成失败: {str(e)}")
        fallback = f"抱歉，我在处理你的请求时遇到了一些困惑：「{anomaly_reason}」。能否请你换一种方式描述你的需求？"
        new_history = list(chat_history)
        new_history.append({"role": "assistant", "content": fallback})
        return {
            "anomaly_clarify": False,
            "anomaly_reason": "",
            "chat_history": new_history,
            "current_step": f"简答智能体: 异常追问降级 - {str(e)}",
            "stream_events": [{
                "event_type": "content",
                "agent": "simple_answer",
                "data": {"text": fallback, "action": "clarify"},
                "step_description": "异常追问澄清（降级）"
            }],
        }


def _should_ask_profile(chat_history: List[Dict[str, str]], profile: Dict[str, Any]) -> bool:
    """判断是否应该主动询问画像问题（低频率触发）"""
    user_turns = sum(1 for m in chat_history if m["role"] == "user")
    if user_turns < 3:
        return False

    # 检查最近是否询问过画像问题
    recent = chat_history[-20:]
    for msg in recent:
        content = msg.get("content", "").lower()
        if any(kw in content for kw in ["学习风格", "偏好", "喜欢", "习惯", "更倾向"]):
            return False

    # 低频率随机触发
    return random.random() < 0.3


def _pick_profile_question(profile: Dict[str, Any]) -> tuple:
    """选择一个画像维度的问题（尽量不重复）"""
    behavior = profile.get("learning_behavior", {})

    candidates = []
    dimension_map = {
        "sensing_vs_intuitive": behavior.get("sensing_vs_intuitive", 0.0) == 0.0,
        "visual_vs_verbal": behavior.get("visual_vs_verbal", 0.0) == 0.0,
        "active_vs_reflective": behavior.get("active_vs_reflective", 0.0) == 0.0,
        "sequential_vs_global": behavior.get("sequential_vs_global", 0.0) == 0.0,
    }

    for dim, is_none in dimension_map.items():
        if is_none:
            candidates.append(dim)

    if not candidates:
        candidates = list(dimension_map.keys())

    for dim in ["knowledge_base", "quiz_preference", "content_preference"]:
        candidates.append(dim)

    chosen = random.choice(candidates)
    questions = PROFILE_QUESTIONS.get(chosen, ["你觉得自己的学习风格是怎样的？"])
    return chosen, random.choice(questions)
