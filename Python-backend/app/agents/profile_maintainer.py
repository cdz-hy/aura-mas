"""
画像维护智能体 - 根据对话记录微调用户画像
所有画像分析调用在后台异步进行，不影响主流程
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_profile_maintainer_llm

logger = logging.getLogger("agents.profile_maintainer")

SYSTEM_PROMPT = """你是一个用户画像分析专家。根据用户的对话内容和学习行为数据，分析并更新用户画像。

## Felder-Silverman 学习风格模型
四个维度，每个维度值在 -1 到 +1 之间：
1. **sensing_intuitive**: 感官型(-1) <-> 直觉型(+1)
2. **visual_verbal**: 视觉型(-1) <-> 言语型(+1)
3. **active_reflective**: 活跃型(-1) <-> 沉思型(+1)
4. **sequential_global**: 序列型(-1) <-> 全局型(+1)

## 输出格式
严格输出 JSON：
{
  "should_update": true/false,
  "update_reason": "更新原因",
  "updates": {
    "felder_silverman": {
      "sensing_intuitive": null,
      "visual_verbal": null,
      "active_reflective": null,
      "sequential_global": null
    },
    "knowledge_base": [],
    "weak_points": [],
    "preferred_quiz_types": [],
    "content_preferences": [],
    "interaction_level": null
  },
  "confidence": 0.8,
  "analysis": "分析过程说明"
}

## 规则
- 只更新有明确证据支持的字段，不确定的设为 null
- Felder-Silverman 维度的调整幅度建议在 0.1-0.3 之间
- confidence 表示本次分析的置信度 (0-1)
- 如果对话中没有画像相关信息，should_update 为 false
- 严禁使用 emoji 表情符号"""


def profile_maintainer_node(state: AgentState) -> Dict[str, Any]:
    """画像维护智能体节点"""
    user_message = state.get("user_message", "")
    chat_history = state.get("chat_history", [])
    user_profile = state.get("user_profile", {})
    quiz_result = state.get("quiz_result")

    logger.info(f"{'='*60}")
    logger.info(f"  [画像维护智能体] 开始处理")
    logger.info(f"  用户输入: {user_message[:80]}")
    logger.info(f"  有答题数据: {'是' if quiz_result else '否'}")

    llm = get_profile_maintainer_llm()

    history_text = ""
    recent = chat_history[-10:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content']}\n"

    current_behavior = user_profile.get("learning_behavior", {})
    current_fs = current_behavior.get("felder_silverman", {})

    quiz_text = ""
    if quiz_result:
        quiz_text = f"""
最近答题情况:
- 题目: {quiz_result.get('question_text', '')}
- 得分: {quiz_result.get('score', 0)}
- 正确: {quiz_result.get('is_correct', False)}
- 命中要点: {', '.join(quiz_result.get('key_points_hit', []))}
- 遗漏要点: {', '.join(quiz_result.get('key_points_missed', []))}"""
        logger.info(f"  [画像维护智能体] 答题得分: {quiz_result.get('score', 0):.0%}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""当前用户画像:
- 领域: {user_profile.get('domain', '未知')}
- 知识基础: {current_behavior.get('knowledge_base', [])}
- 感官-直觉: {current_fs.get('sensing_intuitive', '未评估')}
- 视觉-言语: {current_fs.get('visual_verbal', '未评估')}
- 活跃-沉思: {current_fs.get('active_reflective', '未评估')}
- 序列-全局: {current_fs.get('sequential_global', '未评估')}
- 薄弱点: {current_behavior.get('weak_points', [])}
- 偏好题型: {current_behavior.get('preferred_quiz_types', [])}

对话历史:
{history_text}

当前用户输入: {user_message}
{quiz_text}

请分析是否有需要更新的画像信息，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [画像维护智能体] 正在调用 LLM 分析画像...")
        result = llm.chat_json(messages, max_tokens=2048)
        should_update = result.get("should_update", False)
        updates = result.get("updates", {})
        confidence = result.get("confidence", 0)
        analysis = result.get("analysis", "")

        logger.info(f"  [画像维护智能体] 分析完成!")
        logger.info(f"    需要更新: {'是' if should_update else '否'}")
        logger.info(f"    置信度: {confidence:.2f}")
        logger.info(f"    分析: {analysis[:150]}")

        # 过滤掉 null 值
        filtered_updates = {}
        for key, val in updates.items():
            if val is None:
                continue
            if isinstance(val, dict):
                filtered_inner = {k: v for k, v in val.items() if v is not None}
                if filtered_inner:
                    filtered_updates[key] = filtered_inner
                    logger.info(f"    更新维度 {key}: {filtered_inner}")
            elif isinstance(val, list) and len(val) > 0:
                filtered_updates[key] = val
                logger.info(f"    更新字段 {key}: {val}")
            elif not isinstance(val, (dict, list)):
                filtered_updates[key] = val
                logger.info(f"    更新字段 {key}: {val}")

        logger.info(f"{'='*60}")

        return_data = {
            "profile_update_needed": should_update,
            "current_step": f"画像维护智能体: {'需要更新' if should_update else '无需更新'} (置信度: {confidence})",
        }

        if should_update and filtered_updates:
            return_data["stream_events"] = [{
                "event_type": "profile_update",
                "agent": "profile_maintainer",
                "data": {
                    "updates": filtered_updates,
                    "reason": result.get("update_reason", ""),
                    "confidence": confidence,
                    "analysis": analysis,
                },
                "step_description": f"画像更新: {result.get('update_reason', '')}"
            }]

        return return_data

    except Exception as e:
        logger.error(f"  [画像维护智能体] 分析异常: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "profile_update_needed": False,
            "current_step": f"画像维护智能体: 分析异常 - {str(e)}",
        }
