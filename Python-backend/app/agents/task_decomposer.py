"""
任务分解智能体 - 根据用户画像和学习目标生成个性化学习路径
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER, NODE_HUMAN_CONFIRM
from app.agents.llm_factory import get_task_decomposer_llm

logger = logging.getLogger("agents.task_decomposer")

SYSTEM_PROMPT = """你是一个专业的学习路径规划专家。你的任务是根据用户的学习目标和用户画像，生成或优化个性化的、结构化的学习路径分解。

## 输出要求
严格输出 JSON，格式如下：
{
  "title": "学习计划标题",
  "description": "学习计划简要描述",
  "difficulty_level": "入门/初级/中级/高级",
  "estimated_duration": "预估总学时",
  "prerequisites": ["前置知识1", "前置知识2"],
  "modules": [
    {
      "module_id": 1,
      "title": "模块标题",
      "description": "模块内容描述",
      "key_points": ["要点1", "要点2"],
      "estimated_duration": "预估学时",
      "resource_types": ["text", "diagram", "code", "mindmap", "document"],
      "order": 1
    }
  ],
  "learning_tips": "针对该用户画像的学习建议"
}

## 规则
1. 模块数量控制在 3-8 个，每个模块的内容量适中
2. 根据用户画像中的 Felder-Silverman 模型调整资源类型偏好：
   - 视觉型偏好多图片、流程图、思维导图
   - 言语型偏好详细文字说明
   - 活跃型偏好实操案例和代码示例
   - 沉思型偏好深入分析
   - 序列型偏好循序渐进的步骤
   - 全局型偏好先给整体框架再细分
3. 根据用户的知识基础调整难度和前置知识
4. 严禁使用 emoji 表情符号
5. 所有内容使用中文
6. 模块标题必须是实际内容名称，严禁使用「第一章」「第二章」「模块一」「Part 1」等章节编号前缀，也不要使用「XXX:」等冒号后缀。标题只写实际内容名即可
7. resource_types 中严禁包含 "quiz" 类型！题目/练习题只能由专门的题目生成智能体单独生成，不允许在学习路径规划中出现

## 优化已有学习路径的规则（当收到 existing_plan 时）
当用户提供已有学习路径和补充意见时，你必须在已有路径的基础上进行增量优化，而不是从零开始重新生成：
- 保留已有的模块，不要删除用户未要求修改的内容
- 根据用户补充意见新增模块或调整现有模块
- 保持原有模块的 module_id 不变，新模块使用新的 ID
- 调整模块顺序以保证学习逻辑的连贯性
- 如果用户要求新增主题，将其作为新模块插入到合适的位置
- 如果用户要求修改某个模块，只修改该模块，不要影响其他模块"""


def task_decomposer_node(state: AgentState) -> Dict[str, Any]:
    """任务分解智能体节点"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    user_profile = state.get("user_profile", {})
    human_feedback = state.get("human_feedback", "")
    existing_plan = state.get("task_breakdown")

    logger.info(f"{'='*60}")
    logger.info(f"  [任务分解智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    if human_feedback:
        logger.info(f"  用户补充反馈: {human_feedback[:100]}")
    if existing_plan:
        logger.info(f"  已有学习路径: {existing_plan.get('title', '未命名')}")
    logger.info(f"  用户画像: {'有' if user_profile else '无'}")

    llm = get_task_decomposer_llm()

    profile_summary = _format_profile(user_profile)
    history_prefs = _extract_preferences(state.get("chat_history", []))

    # 构造对话历史上下文
    chat_history = state.get("chat_history", [])
    history_text = ""
    if chat_history:
        recent = chat_history[-8:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    logger.info(f"  [任务分解智能体] 画像摘要: {profile_summary[:200]}")

    # 有已有计划 + 用户反馈 → 增量优化模式
    if existing_plan and human_feedback:
        import json as _json
        existing_plan_text = _json.dumps(existing_plan, ensure_ascii=False, indent=2)
        user_prompt = f"""已有学习路径需要根据用户反馈进行优化。

## 已有学习路径（请在此基础上优化，不要从零开始）
```json
{existing_plan_text}
```

## 用户补充/修改意见
{human_feedback}

## 学习目标
{learning_goal}

## 对话历史（请结合上下文理解用户意图）
{history_text if history_text else "无历史记录"}

## 用户画像
{profile_summary}

## 用户对话中表达的偏好
{history_prefs}

请根据用户意见在已有路径基础上优化，输出完整的学习路径 JSON："""
    else:
        # 全新生成模式
        user_prompt = f"""请根据以下信息生成学习路径分解：

## 学习目标
{learning_goal}

## 对话历史（请结合上下文理解用户意图）
{history_text if history_text else "无历史记录"}

## 用户画像
{profile_summary}

## 用户对话中表达的偏好
{history_prefs}

请输出 JSON 格式的学习路径分解："""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        logger.info(f"  [任务分解智能体] 正在调用 LLM 生成学习路径...")
        result = llm.chat_json(messages)

        modules = result.get("modules", [])
        logger.info(f"  [任务分解智能体] 学习路径生成成功!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    难度: {result.get('difficulty_level', '未知')}")
        logger.info(f"    预估时长: {result.get('estimated_duration', '未知')}")
        logger.info(f"    模块数量: {len(modules)}")
        for i, m in enumerate(modules):
            logger.info(f"      模块{i+1}: {m.get('title', '')} - {m.get('description', '')[:50]}")
        logger.info(f"  [任务分解智能体] 等待用户确认")
        logger.info(f"{'='*60}")

        return {
            "task_breakdown": result,
            "learning_goal": learning_goal,
            "task_breakdown_confirmed": False,
            "human_feedback": None,  # 清除已处理的反馈，防止路由死循环
            "needs_human_confirm": True,  # 标记需要用户确认新生成的计划
            "current_step": f"任务分解智能体: 已生成学习路径 [{result.get('title', '未命名')}]，包含 {len(modules)} 个模块",
            "stream_events": [
                {
                    "event_type": "task_breakdown",
                    "agent": "task_decomposer",
                    "data": result,
                    "step_description": "学习路径规划完成，请确认或补充说明"
                },
                {
                    "event_type": "confirm_needed",
                    "agent": "task_decomposer",
                    "data": {
                        "message": "学习路径已优化，请确认或继续补充",
                        "task_breakdown": result,
                    },
                    "step_description": "请确认学习路径"
                },
            ],
        }
    except Exception as e:
        logger.error(f"  [任务分解智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"任务分解失败: {str(e)}",
            "current_step": f"任务分解智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "task_decomposer",
                "data": {"error": str(e)},
                "step_description": "任务分解失败"
            }],
        }


def _format_profile(profile: Dict[str, Any]) -> str:
    """格式化用户画像为文本摘要"""
    if not profile:
        return "暂无用户画像信息"

    parts = []
    if profile.get("domain"):
        parts.append(f"领域: {profile['domain']}")
    if profile.get("age"):
        parts.append(f"年龄: {profile['age']}")

    behavior = profile.get("learning_behavior", {})
    if behavior:
        knowledge = behavior.get("knowledge_base", [])
        if knowledge:
            parts.append(f"已有知识基础: {', '.join(knowledge)}")

        fs = behavior.get("felder_silverman", {})
        if fs:
            dimensions = []
            si = fs.get("sensing_intuitive", 0)
            dimensions.append(f"{'感官型' if si < 0 else '直觉型'}(倾向度: {abs(si):.1f})")
            vv = fs.get("visual_verbal", 0)
            dimensions.append(f"{'视觉型' if vv < 0 else '言语型'}(倾向度: {abs(vv):.1f})")
            ar = fs.get("active_reflective", 0)
            dimensions.append(f"{'活跃型' if ar < 0 else '沉思型'}(倾向度: {abs(ar):.1f})")
            sg = fs.get("sequential_global", 0)
            dimensions.append(f"{'序列型' if sg < 0 else '全局型'}(倾向度: {abs(sg):.1f})")
            parts.append(f"学习风格: {'; '.join(dimensions)}")

        weak_points = behavior.get("weak_points", [])
        if weak_points:
            parts.append(f"薄弱点: {', '.join(weak_points)}")

        pref_quiz = behavior.get("preferred_quiz_types", [])
        if pref_quiz:
            parts.append(f"偏好题型: {', '.join(pref_quiz)}")

        prefs = behavior.get("content_preferences", [])
        if prefs:
            parts.append(f"内容偏好: {', '.join(prefs)}")

    return "\n".join(parts) if parts else "暂无详细画像信息"


def _extract_preferences(chat_history: List[Dict[str, str]]) -> str:
    """从对话历史中提取用户偏好"""
    if not chat_history:
        return "暂无对话记录"

    recent_user = [m["content"] for m in chat_history if m["role"] == "user"][-5:]
    if not recent_user:
        return "暂无用户发言"

    return "用户近期发言:\n" + "\n".join(f"- {m}" for m in recent_user)
