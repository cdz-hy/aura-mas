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
from app.utils import stream_registry
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
}

# 目标导向问题
GOAL_QUESTIONS = [
    "你目前学习的主要目标是什么？是为了考试、职业发展、兴趣探索，还是提升某项具体技能？",
    "你希望在学习中达到什么样的效果？是掌握理论基础，还是能实际应用解决问题？",
    "你学习的动力更多来自外部要求（如考试、工作）还是内在兴趣？",
]

# 偏好资源类型问题
RESOURCE_QUESTIONS = [
    "在学习资源方面，你更偏好视频讲解、图文教程、流程图，还是代码示例？",
    "你学习时更喜欢看实际案例分析，还是理论知识的系统梳理？",
    "如果要学一个新概念，你会优先选择看视频、读文章、还是动手做实验？",
]


def _build_knowledge_question(profile: Dict[str, Any]) -> str:
    """基于用户已有知识生成问题"""
    behavior = profile.get("learning_behavior", {})
    knowledge = behavior.get("knowledge_base", [])
    if knowledge:
        sample = random.sample(knowledge, min(3, len(knowledge)))
        return f"你之前学过「{'、'.join(sample)}」这些内容，现在对它们的掌握程度如何？有没有哪些已经忘了或者想重新复习的？"
    return "你之前有学过哪些相关的课程或知识吗？对当前学习的内容了解程度如何？"


def _build_interest_question(profile: Dict[str, Any]) -> str:
    """基于用户兴趣标签生成问题，询问是否还感兴趣"""
    behavior = profile.get("learning_behavior", {})
    tags = behavior.get("interest_tags", [])
    if tags:
        sample = random.sample(tags, min(3, len(tags)))
        return f"你之前的兴趣方向包括「{'、'.join(sample)}」，现在还对这些感兴趣吗？有没有不感兴趣的可以去掉，或者想新增的？"
    return "你目前对哪些学习方向或话题比较感兴趣？可以告诉我，我会帮你记录偏好。"


def simple_answer_node(state: AgentState) -> Dict[str, Any]:
    """简答智能体节点"""
    user_message = state.get("user_message", "")
    chat_history = state.get("chat_history", [])
    user_profile = state.get("user_profile", {})

    logger.info(f"{'='*60}")
    logger.info(f"  [简答智能体] 开始处理")
    logger.info(f"  用户输入: {user_message[:100]}")

    # 实时推送思考过程
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))

    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "简答智能体", "content": content}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_start(agent: str, prefix: str = ""):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_start", "agent": agent, "content": prefix}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    _emit_thinking("正在理解你的问题并组织回答...")

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

    # 判断是否应该主动询问画像
    should_ask_profile = _should_ask_profile(chat_history, user_profile)
    profile_hint = ""
    asked_profile_dim = None  # 记录本次询问的画像维度

    if should_ask_profile:
        dim, question = _pick_profile_question(user_profile)
        profile_hint = f"\n\n[系统建议] 可以自然地询问用户关于「{dim}」的问题，参考问题: {question}\n如果是兴趣标签问题，用户说不感兴趣的标签需要记录删除。"
        asked_profile_dim = dim
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
                    sse_cb(f'data: {json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}\n\n')
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

        # 如果问了画像问题，添加标记让主控智能体知道
        if asked_profile_dim:
            return_data["_asked_profile_question"] = asked_profile_dim
            logger.info(f"  [简答智能体] 标记询问画像维度: {asked_profile_dim}")
        else:
            # 没有问画像问题，清除标记
            return_data["_asked_profile_question"] = ""

        # 添加通用提问标记：如果 LLM 的 action 是 clarify/ask_profile，或者回复以疑问语气结尾
        has_question = False
        if action in ["clarify", "ask_profile"]:
            has_question = True
        elif response:
            clean_resp = response.strip()
            if clean_resp and clean_resp[-1] in ["?", "？"]:
                has_question = True
            elif clean_resp and any(clean_resp.endswith(q) for q in ["吗", "呢", "吗？", "呢？"]):
                has_question = True
        
        return_data["_pending_question"] = has_question
        if has_question:
            logger.info(f"  [简答智能体] 检测到主动提问，已设置 _pending_question=True")
        else:
            return_data["_pending_question"] = False

        # 更新对话历史
        new_history = list(chat_history)
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": response})
        return_data["chat_history"] = new_history

        # 如果检测到画像信息，标记需要更新（支持所有画像特征维度）
        valid_dimensions = [
            "visual_vs_verbal", "active_vs_reflective", "sensing_vs_intuitive", "sequential_vs_global",
            "visual_verbal", "active_reflective", "sensing_intuitive", "sequential_global",
            "knowledge_base", "weak_areas", "interest_tags", "preferred_resource_types", "preferred_quiz_types", "goal_orientation"
        ]
        has_profile_info = should_update or (profile_dimension in valid_dimensions)

        if has_profile_info:
            mapped_dimension = map_dimension_name(profile_dimension) if profile_dimension else "general_profile"
            return_data["profile_update_needed"] = True
            return_data["stream_events"].append({
                "event_type": "profile_update",
                "agent": "simple_answer",
                "data": {
                    "dimension": mapped_dimension,
                    "answer": user_message,
                    "analysis": profile_analysis or "检测到画像相关对话",
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
        sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))

        def _on_chunk(chunk: str):
            if sse_cb:
                try:
                    sse_cb(f'data: {json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        logger.info(f"  [简答智能体] 正在流式生成异常追问回复...")
        result = llm.chat_json_stream(messages, on_chunk=_on_chunk, stream_field="response")
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
    """判断是否应该主动询问画像问题（总概率60%）"""
    # 总概率60%
    return random.random() < 0.6


def _pick_profile_question(profile: Dict[str, Any]) -> tuple:
    """选择一个画像维度的问题（按概率分配）"""
    behavior = profile.get("learning_behavior", {})

    # 概率分配：学习风格20%，目标导向10%，偏好资源10%，知识基础10%，兴趣标签10%
    rand = random.random()

    # 20% 概率询问学习风格维度
    if rand < 0.20:
        # 优先询问数据缺失的维度
        candidates = []
        dimension_map = {
            "sensing_vs_intuitive": abs(behavior.get("sensing_vs_intuitive", 0)) < 0.01,
            "visual_vs_verbal": abs(behavior.get("visual_vs_verbal", 0)) < 0.01,
            "active_vs_reflective": abs(behavior.get("active_vs_reflective", 0)) < 0.01,
            "sequential_vs_global": abs(behavior.get("sequential_vs_global", 0)) < 0.01,
        }
        for dim, is_none in dimension_map.items():
            if is_none:
                candidates.append(dim)
        if not candidates:
            candidates = list(dimension_map.keys())
        chosen = random.choice(candidates)
        questions = PROFILE_QUESTIONS.get(chosen, ["你觉得自己的学习风格是怎样的？"])
        return chosen, random.choice(questions)

    # 10% 概率询问目标导向
    if rand < 0.30:
        return "goal_orientation", random.choice(GOAL_QUESTIONS)

    # 10% 概率询问偏好资源
    if rand < 0.40:
        return "preferred_resource_types", random.choice(RESOURCE_QUESTIONS)

    # 10% 概率询问知识基础
    if rand < 0.50:
        return "knowledge_base", _build_knowledge_question(profile)

    # 10% 概率询问兴趣标签
    if rand < 0.60:
        return "interest_tags", _build_interest_question(profile)

    # 兜底（不会触发，因为总概率是60%）
    return "goal_orientation", random.choice(GOAL_QUESTIONS)
