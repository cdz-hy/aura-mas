"""
简答智能体 - 简短回答用户问题，决定是否追问，维护对话上下文
可主动询问学习满意度、学习要求、Felder-Silverman 模型相关问题
"""
import logging
import random
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER
from app.agents.llm_factory import get_simple_answer_llm
from app.utils.profile_utils import map_dimension_name

logger = logging.getLogger("agents.simple_answer")

SYSTEM_PROMPT = """你是一个友好的 AI 学习助手。你的职责是：
1. 简短回答用户的知识性问题
2. 当用户意图不明确时，进行追问以获取清晰的目标
3. 维护自然流畅的对话
4. **主动识别和捕捉用户的学习风格信息**

## 规则
- 回答简洁明了，避免冗长
- 如果用户的问题很模糊，礼貌地追问具体需求
- 严禁使用 emoji 表情符号
- 保持专业但亲切的语气
- 使用中文回复

## 学习画像维度说明

### Felder-Silverman 学习风格模型（4个维度）
1. **sensing_intuitive** - 信息感知维度
   - Sensing（感官型）：偏好具体事实、数据、实验、实例
   - Intuitive（直觉型）：偏好抽象概念、理论、创新、可能性

2. **visual_verbal** - 信息接收维度
   - Visual（视觉型）：偏好图表、图示、流程图、视频
   - Verbal（言语型）：偏好文字说明、口头讲解、书面材料

3. **active_reflective** - 信息处理维度
   - Active（活跃型）：偏好动手实践、小组讨论、边做边学
   - Reflective（沉思型）：偏好独自思考、深度分析、先想后做

4. **sequential_global** - 理解方式维度
   - Sequential（序列型）：偏好线性学习、逐步深入、按部就班
   - Global（全局型）：偏好整体把握、先见森林后见树木、跳跃式理解

### 其他画像维度
- **knowledge_base** - 知识基础：用户已掌握的相关知识
- **quiz_preference** - 偏好题型：选择题、填空题、简答题等
- **interaction_level** - 交互程度：喜欢频繁互动还是独立学习
- **content_preference** - 内容偏好：视频、图文、代码示例等

## 画像信息识别（核心能力）

**你需要主动判断：**
1. 对话历史中，你是否刚刚询问了用户关于学习风格的问题？
2. 当前用户的回答是否是对你刚才问题的响应？
3. 用户的回答揭示了哪个维度的学习风格？

**判断标准：**
- 如果你上一轮询问了学习偏好相关的问题（如"你更喜欢A还是B？"），而用户当前回答是简短的选择或描述（如"A"、"我喜欢B"、"都可以"），则很可能是对画像问题的回答
- 即使用户没有直接回答你的问题，但在对话中透露了学习偏好信息，也应该捕捉
- 根据用户回答的内容，判断属于哪个维度

**重要：** 充分发挥你的理解能力，不要机械地匹配关键词。理解对话的上下文和用户的真实意图。

## 输出要求
严格输出 JSON：
{
  "action": "answer" 或 "clarify" 或 "ask_profile",
  "response": "你的回复文本",
  "should_update_profile": false,
  "profile_dimension": null,
  "profile_analysis": null
}

### 字段说明
- **action**: 
  - "answer" - 正常回答问题
  - "clarify" - 需要追问澄清
  - "ask_profile" - 主动询问学习风格
  
- **should_update_profile**: 
  - true - 当前对话包含了可用于更新画像的信息
  - false - 没有画像相关信息
  
- **profile_dimension**: 
  - 当 should_update_profile=true 时必填
  - 填写用户回答涉及的维度（可以是上述任一维度）
  
- **profile_analysis**: 
  - 当 should_update_profile=true 时必填
  - 简短说明你从用户回答中理解到的学习风格信息（1-2句话）
  - 例如："用户表示更喜欢看图，倾向于视觉型学习"

## 示例

### 示例1：识别画像回答
对话历史：
助手: 当理解一个复杂概念时，一张好的示意图和一段详细的文字解释，哪个对你帮助更大？
用户: 想看图！

输出：
{
  "action": "answer",
  "response": "好的，我了解了！我会为你提供更多图示化的内容来帮助理解。",
  "should_update_profile": true,
  "profile_dimension": "visual_verbal",
  "profile_analysis": "用户明确表示更喜欢图示，属于视觉型学习者"
}

### 示例2：识别隐含的画像信息
对话历史：
用户: 我想学习红黑树，但是看文字描述总是看不懂，有没有动画演示？

输出：
{
  "action": "answer",
  "response": "当然！红黑树的动画演示能帮助你更直观地理解插入和旋转操作...",
  "should_update_profile": true,
  "profile_dimension": "visual_verbal",
  "profile_analysis": "用户提到看文字描述困难，需要动画演示，明显偏好视觉型学习"
}

### 示例3：主动询问画像
{
  "action": "ask_profile",
  "response": "为了更好地帮助你学习，我想了解一下：学完一个新知识点后，你更喜欢立刻动手实践尝试，还是先在脑海中反复思考消化？",
  "should_update_profile": false,
  "profile_dimension": null,
  "profile_analysis": null
}"""


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

    # 构建对话历史文本（包含更多轮次以便 LLM 理解上下文）
    history_text = ""
    recent = chat_history[-10:]  # 增加到10轮，让 LLM 有更多上下文
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
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""对话历史:
{history_text}

当前用户输入: {user_message}
{profile_hint}

请分析对话上下文，判断是否包含学习风格信息，并输出 JSON:"""}
    ]

    try:
        logger.info(f"  [简答智能体] 正在调用 LLM 生成回复...")
        result = llm.chat_json(messages)
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


def _should_ask_profile(chat_history: List[Dict[str, str]], profile: Dict[str, Any]) -> bool:
    """判断是否应该主动询问画像问题（低频率触发）"""
    user_turns = sum(1 for m in chat_history if m["role"] == "user")
    if user_turns < 3:
        return False

    # 检查最近是否询问过画像问题
    recent = chat_history[-10:]
    for msg in recent:
        content = msg.get("content", "").lower()
        if any(kw in content for kw in ["学习风格", "偏好", "喜欢", "习惯", "更倾向"]):
            return False

    # 低频率随机触发
    return random.random() < 0.3


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
