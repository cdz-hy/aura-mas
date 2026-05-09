"""
简答智能体 - 简短回答用户问题，决定是否追问，维护对话上下文
可主动询问学习满意度、学习要求、Felder-Silverman 模型相关问题
"""
import logging
import random
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER
from app.agents.llm_factory import get_simple_answer_llm

logger = logging.getLogger("agents.simple_answer")

SYSTEM_PROMPT = """你是一个友好的 AI 学习助手。你的职责是：
1. 简短回答用户的知识性问题
2. 当用户意图不明确时，进行追问以获取清晰的目标
3. 维护自然流畅的对话

## 规则
- 回答简洁明了，避免冗长
- 如果用户的问题很模糊，礼貌地追问具体需求
- 严禁使用 emoji 表情符号
- 保持专业但亲切的语气
- 使用中文回复

## 输出要求
严格输出 JSON：
{
  "action": "answer" 或 "clarify" 或 "ask_profile",
  "response": "你的回复文本",
  "should_update_profile": false,
  "profile_question": null,
  "profile_dimension": null
}

当 action 为 "ask_profile" 时，profile_question 填写你想询问的问题，profile_dimension 填写对应的维度：
- "sensing_intuitive" - 信息感知维度
- "visual_verbal" - 信息接收维度
- "active_reflective" - 信息处理维度
- "sequential_global" - 理解方式维度
- "knowledge_base" - 知识基础
- "quiz_preference" - 偏好题型
- "interaction_level" - 交互程度
- "content_preference" - 内容偏好"""


PROFILE_QUESTIONS = {
    "sensing_intuitive": [
        "在学习新知识时，你更倾向于通过具体的实例和实验来理解，还是更喜欢先了解抽象的理论和概念框架？",
        "如果让你学习一个新的技术概念，你会更喜欢看一个完整的实际案例演示，还是先阅读理论原理的阐述？",
        "你觉得自己在学习时是更注重细节和事实，还是更善于把握整体的概念和关联？",
    ],
    "visual_verbal": [
        "你学习时更喜欢看图表、流程图、思维导图这类视觉化的内容，还是更喜欢阅读详细的文字说明？",
        "当理解一个复杂概念时，一张好的示意图和一段详细的文字解释，哪个对你帮助更大？",
        "你平时记笔记时更习惯画图示还是写文字？",
    ],
    "active_reflective": [
        "学完一个新知识点后，你更喜欢立刻动手实践尝试，还是先在脑海中反复思考消化？",
        "你更喜欢通过小组讨论来加深理解，还是独自安静地思考？",
        "面对一个新的学习任务，你的第一反应是马上开始动手做，还是先花时间规划和思考？",
    ],
    "sequential_global": [
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

    llm = get_simple_answer_llm()

    history_text = ""
    recent = chat_history[-8:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content']}\n"

    should_ask_profile = _should_ask_profile(chat_history, user_profile)
    profile_hint = ""
    if should_ask_profile:
        dim, question = _pick_profile_question(user_profile)
        profile_hint = f"\n\n[系统提示] 建议你适时询问用户关于学习风格的问题，当前建议维度: {dim}，参考问题: {question}"
        logger.info(f"  [简答智能体] 触发画像询问: 维度={dim}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""对话历史:
{history_text}

当前用户输入: {user_message}
{profile_hint}

请输出 JSON:"""}
    ]

    try:
        logger.info(f"  [简答智能体] 正在调用 LLM 生成回复...")
        result = llm.chat_json(messages)
        response = result.get("response", "")
        action = result.get("action", "answer")
        should_update = result.get("should_update_profile", False)

        logger.info(f"  [简答智能体] 回复类型: {action}")
        logger.info(f"  [简答智能体] 回复内容: {response[:150]}")
        if should_update:
            logger.info(f"  [简答智能体] 检测到画像更新信号: 维度={result.get('profile_dimension')}")
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

        new_history = list(chat_history)
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": response})
        return_data["chat_history"] = new_history

        if should_update and result.get("profile_dimension"):
            return_data["profile_update_needed"] = True
            return_data["stream_events"].append({
                "event_type": "profile_update",
                "agent": "simple_answer",
                "data": {
                    "dimension": result["profile_dimension"],
                    "question": result.get("profile_question"),
                    "answer": user_message,
                },
                "step_description": "检测到画像相关信息，后台更新中"
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


def _should_ask_profile(chat_history: List[Dict[str, str]], profile: Dict[str, Any]) -> bool:
    """判断是否应该主动询问画像问题"""
    user_turns = sum(1 for m in chat_history if m["role"] == "user")
    if user_turns < 3:
        return False

    recent = chat_history[-10:]
    for msg in recent:
        content = msg.get("content", "").lower()
        if any(kw in content for kw in ["学习风格", "偏好", "喜欢", "习惯", "风格"]):
            return False

    return random.random() < 0.2


def _pick_profile_question(profile: Dict[str, Any]) -> tuple:
    """选择一个画像维度的问题（尽量不重复）"""
    behavior = profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})

    candidates = []
    dimension_map = {
        "sensing_intuitive": fs.get("sensing_intuitive") is None,
        "visual_verbal": fs.get("visual_verbal") is None,
        "active_reflective": fs.get("active_reflective") is None,
        "sequential_global": fs.get("sequential_global") is None,
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
