"""
任务分解智能体 - 根据用户画像和学习目标生成个性化学习路径
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER, NODE_HUMAN_CONFIRM
from app.agents.llm_factory import get_task_decomposer_llm
from app.prompts import TASK_DECOMPOSER_PROMPT
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("agents.task_decomposer")


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
        {"role": "system", "content": TASK_DECOMPOSER_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        logger.info(f"  [任务分解智能体] 正在调用 LLM 生成学习路径...")
        result = llm.chat_json(messages)
        record_from_mimo(llm, state.get("user_id", 0), "task_decomposition", state.get("task_id"))

        modules = result.get("modules", [])
        needs_decomposition = result.get("needs_decomposition", len(modules) > 1)
        analysis = result.get("analysis", "")

        logger.info(f"  [任务分解智能体] 学习路径生成成功!")
        logger.info(f"    需分解: {'是' if needs_decomposition else '否 (单模块直接生成)'}")
        if analysis:
            logger.info(f"    分析: {analysis[:120]}")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    难度: {result.get('difficulty_level', '未知')}")
        logger.info(f"    预估时长: {result.get('estimated_duration', '未知')}")
        logger.info(f"    模块数量: {len(modules)}")
        for i, m in enumerate(modules):
            logger.info(f"      模块{i+1}: {m.get('title', '')} - {m.get('description', '')[:50]}")

        # 自主异常检测：检查分解内容是否与原始目标偏离
        anomaly_summary = f"标题: {result.get('title', '')}; 模块: " + "; ".join(
            f"{m.get('title', '')}: {m.get('description', '')}" for m in modules[:3]
        )
        from app.agents.anomaly_checker import check_content_alignment
        is_aligned, anomaly_reason = check_content_alignment(learning_goal, anomaly_summary)
        if not is_aligned:
            logger.warning(f"  [任务分解智能体] 自主检测到内容偏离: {anomaly_reason}")
            logger.warning(f"  [任务分解智能体] 中断当前流程 -> 回到主控")
            return {
                "agent_anomaly": True,
                "anomaly_reason": anomaly_reason,
                "current_step": f"任务分解智能体: 检测到内容偏离 - {anomaly_reason}",
                "stream_events": [{
                    "event_type": "thinking",
                    "agent": "task_decomposer",
                    "data": {"message": f"检测到分解内容与原始目标偏离: {anomaly_reason}"},
                    "step_description": f"异常中断: {anomaly_reason}"
                }],
            }

        logger.info(f"{'='*60}")

        if needs_decomposition:
            # 多模块 → 需要用户确认
            logger.info(f"  [任务分解智能体] 进入用户确认流程")
            return {
                "task_breakdown": result,
                "learning_goal": learning_goal,
                "task_breakdown_confirmed": False,
                "human_feedback": None,
                "needs_human_confirm": True,
                "current_step": f"任务分解智能体: 已生成学习路径 [{result.get('title', '未命名')}]，包含 {len(modules)} 个模块，等待确认",
                "stream_events": [
                    {
                        "event_type": "task_breakdown",
                        "agent": "task_decomposer",
                        "data": result,
                        "step_description": f"学习路径规划完成 ({len(modules)} 个模块)，请确认或补充说明"
                    },
                    {
                        "event_type": "confirm_needed",
                        "agent": "task_decomposer",
                        "data": {
                            "message": f"分析: {analysis}\n\n学习路径已生成，请确认或继续补充",
                            "task_breakdown": result,
                        },
                        "step_description": "请确认学习路径"
                    },
                ],
            }
        else:
            # 单模块 → 自动确认，跳过人工确认直接进入 RAG 检索
            logger.info(f"  [任务分解智能体] 单模块主题，自动确认，跳过人工确认 -> RAG检索")
            return {
                "task_breakdown": result,
                "learning_goal": learning_goal,
                "task_breakdown_confirmed": True,
                "human_feedback": None,
                "needs_human_confirm": False,
                "current_step": f"任务分解智能体: 识别为单模块主题 [{result.get('title', '未命名')}]，直接进入检索",
                "stream_events": [
                    {
                        "event_type": "task_breakdown",
                        "agent": "task_decomposer",
                        "data": result,
                        "step_description": f"识别为聚焦主题: {analysis}"
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

        si = behavior.get("sensing_vs_intuitive", 0)
        vv = behavior.get("visual_vs_verbal", 0)
        ar = behavior.get("active_vs_reflective", 0)
        sg = behavior.get("sequential_vs_global", 0)
        if any([si, vv, ar, sg]):
            dimensions = []
            dimensions.append(f"{'感官型' if si < 0 else '直觉型'}(倾向度: {abs(si):.1f})")
            dimensions.append(f"{'视觉型' if vv < 0 else '言语型'}(倾向度: {abs(vv):.1f})")
            dimensions.append(f"{'活跃型' if ar < 0 else '沉思型'}(倾向度: {abs(ar):.1f})")
            dimensions.append(f"{'序列型' if sg < 0 else '全局型'}(倾向度: {abs(sg):.1f})")
            parts.append(f"学习风格: {'; '.join(dimensions)}")

        weak_points = behavior.get("weak_areas", [])
        if weak_points:
            parts.append(f"薄弱点: {', '.join(weak_points)}")

        pref_quiz = behavior.get("preferred_quiz_types", [])
        if pref_quiz:
            parts.append(f"偏好题型: {', '.join(pref_quiz)}")

        prefs = behavior.get("preferred_resource_types", [])
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
