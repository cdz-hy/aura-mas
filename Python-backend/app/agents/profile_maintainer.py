"""
画像维护智能体 - 根据对话记录微调用户画像
所有画像分析调用在后台异步进行，不影响主流程
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_profile_maintainer_llm
from app.prompts import PROFILE_MAINTAINER_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.utils.profile_utils import (
    ensure_learning_behavior_fields,
    update_learning_behavior,
    map_dimension_name,
)

logger = logging.getLogger("agents.profile_maintainer")



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
    recent = chat_history[-20:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content']}\n"

    # 确保 learning_behavior 字段完整
    current_behavior = user_profile.get("learning_behavior", {})
    current_behavior = ensure_learning_behavior_fields(current_behavior)

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
        {"role": "system", "content": PROFILE_MAINTAINER_PROMPT},
        {"role": "user", "content": f"""当前用户画像:
- 领域: {user_profile.get('domain', '未知')}
- 知识基础: {current_behavior.get('knowledge_base', [])}
- 薄弱点: {current_behavior.get('weak_areas', [])}
- 兴趣标签: {current_behavior.get('interest_tags', [])}
- 视觉-言语: {current_behavior.get('visual_vs_verbal', 0.0)}
- 活跃-沉思: {current_behavior.get('active_vs_reflective', 0.0)}
- 感官-直觉: {current_behavior.get('sensing_vs_intuitive', 0.0)}
- 序列-全局: {current_behavior.get('sequential_vs_global', 0.0)}
- 偏好资源类型: {current_behavior.get('preferred_resource_types', [])}
- 目标导向: {current_behavior.get('goal_orientation', 'exam')}

对话历史:
{history_text}

当前用户输入: {user_message}
{quiz_text}

请分析是否有需要更新的画像信息，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [画像维护智能体] 正在调用 LLM 分析画像...")
        result = llm.chat_json(messages, max_tokens=2048)
        record_from_mimo(llm, state.get("user_id", 0), "profile_maintenance", state.get("task_id"))
        should_update = result.get("should_update", False)
        updates = result.get("updates", {})
        confidence = result.get("confidence", 0)
        analysis = result.get("analysis", "")

        logger.info(f"  [画像维护智能体] 分析完成!")
        logger.info(f"    需要更新: {'是' if should_update else '否'}")
        logger.info(f"    置信度: {confidence:.2f}")
        logger.info(f"    分析: {analysis[:150]}")

        # 使用工具函数更新画像
        if should_update and updates:
            updated_behavior = update_learning_behavior(
                current=current_behavior,
                updates=updates,
                confidence=confidence
            )
            
            # 记录更新的字段
            for key, value in updates.items():
                if value is not None:
                    logger.info(f"    更新字段 {key}: {value}")
            
            logger.info(f"{'='*60}")

            return_data = {
                "profile_update_needed": True,
                "updated_learning_behavior": updated_behavior,
                "current_step": f"画像维护智能体: 需要更新 (置信度: {confidence})",
                "stream_events": [{
                    "event_type": "profile_update",
                    "agent": "profile_maintainer",
                    "data": {
                        "updates": updates,
                        "updated_behavior": updated_behavior,
                        "reason": result.get("update_reason", ""),
                        "confidence": confidence,
                        "analysis": analysis,
                    },
                    "step_description": f"画像更新: {result.get('update_reason', '')}"
                }]
            }
            
            return return_data
        else:
            logger.info(f"{'='*60}")
            return {
                "profile_update_needed": False,
                "current_step": f"画像维护智能体: 无需更新",
            }

    except Exception as e:
        logger.error(f"  [画像维护智能体] 分析异常: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "profile_update_needed": False,
            "current_step": f"画像维护智能体: 分析异常 - {str(e)}",
        }
