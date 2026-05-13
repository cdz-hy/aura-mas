"""
画像维护智能体 - 根据对话记录微调用户画像
所有画像分析调用在后台异步进行，不影响主流程
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_profile_maintainer_llm
from app.utils.profile_utils import (
    ensure_learning_behavior_fields,
    update_learning_behavior,
    map_dimension_name,
)

logger = logging.getLogger("agents.profile_maintainer")

SYSTEM_PROMPT = """你是一个用户画像分析专家。根据用户的对话内容和学习行为数据，分析并更新用户画像。

## 用户画像字段结构

### Felder-Silverman 学习风格维度
四个维度，每个维度值在 -1 到 +1 之间：
1. **visual_vs_verbal**: 视觉型(-1) <-> 言语型(+1)
2. **active_vs_reflective**: 活跃型(-1) <-> 沉思型(+1)
3. **sensing_vs_intuitive**: 感官型(-1) <-> 直觉型(+1)
4. **sequential_vs_global**: 序列型(-1) <-> 全局型(+1)

### 知识与能力
- **knowledge_base**: 已掌握的知识领域列表
- **weak_areas**: 薄弱知识点列表
- **interest_tags**: 兴趣标签列表

### 学习偏好
- **preferred_resource_types**: 偏好的资源类型列表（如 "video", "diagram", "text", "code"）
- **goal_orientation**: 目标导向（"career", "exam", "interest", "skill"）

### 扩展字段（可选）
- **learning_speed**: 学习速度评分 (0-1)
- **engagement_level**: 参与度评分 (0-1)
- **preferred_difficulty**: 偏好难度 (1-5)
- **quiz_accuracy**: 答题准确率 (0-1)

## 输出格式
严格输出 JSON：
{
  "should_update": true/false,
  "update_reason": "更新原因",
  "updates": {
    "visual_vs_verbal": null,
    "active_vs_reflective": null,
    "sensing_vs_intuitive": null,
    "sequential_vs_global": null,
    "knowledge_base": [],
    "weak_areas": [],
    "interest_tags": [],
    "preferred_resource_types": [],
    "goal_orientation": null,
    "learning_speed": null,
    "engagement_level": null,
    "preferred_difficulty": null
  },
  "confidence": 0.8,
  "analysis": "分析过程说明"
}

## 更新规则
1. **学习风格维度**: 调整幅度建议在 0.1-0.3 之间，系统会自动累加到当前值。**符号规则（非常重要）**：
   - 用户偏好**正端**时，输出**正数**（+0.2）；偏好**负端**时，输出**负数**（-0.2）
   - 具体方向：
     - `visual_vs_verbal`: 视觉型偏好 → 负数；言语型偏好 → 正数
     - `active_vs_reflective`: 活跃型偏好 → 负数；沉思型偏好 → 正数
     - `sensing_vs_intuitive`: 感官型偏好 → 负数；直觉型偏好 → 正数
     - `sequential_vs_global`: 序列型偏好 → 负数；全局型偏好 → 正数
2. **列表字段（重要）**: 输出的是你期望该字段的**最终完整状态**，系统会直接替换。你需要结合当前画像内容，判断哪些该保留、哪些该删除、哪些该新增。
   - 设为 `null` 表示不更新此字段
   - 设为 `[]` 表示清空
   - 设为 `["A", "B"]` 表示最终只保留 A 和 B
3. **置信度**: 影响学习风格维度的调整幅度，低置信度时调整更保守
4. **只更新有明确证据的字段**: 不确定的设为 null
5. **严禁使用 emoji 表情符号**

## 示例

### 示例1：识别视觉型偏好
用户说："我看文字总是看不懂，能给我画个图吗？"

输出：
{
  "should_update": true,
  "update_reason": "用户明确表达视觉型学习偏好",
  "updates": {
    "visual_vs_verbal": -0.3,
    "preferred_resource_types": ["diagram", "video"]
  },
  "confidence": 0.9,
  "analysis": "用户表示文字理解困难，需要图示辅助，明显偏好视觉型学习"
}

### 示例2：兴趣标签的增删
当前画像: interest_tags = ["游戏", "编程"]
用户说："我喜欢前端开发，不喜欢游戏了"

输出：
{
  "should_update": true,
  "update_reason": "用户兴趣发生变化：放弃游戏，新增前端开发",
  "updates": {
    "interest_tags": ["编程", "前端开发"]
  },
  "confidence": 0.95,
  "analysis": "用户明确表示不喜欢游戏（应删除），对前端开发感兴趣（应新增），编程保留"
}

### 示例3：知识基础的增删
当前画像: knowledge_base = ["Python", "Redis"]
用户说："我已经忘了 Redis，但最近学了 Docker"

输出：
{
  "should_update": true,
  "update_reason": "用户知识基础变化：遗忘 Redis，新增 Docker",
  "updates": {
    "knowledge_base": ["Python", "Docker"]
  },
  "confidence": 0.9,
  "analysis": "用户明确表示已遗忘 Redis（应删除），新学了 Docker（应新增），Python 保留"
}"""


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
        {"role": "system", "content": SYSTEM_PROMPT},
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
- 目标导向: {current_behavior.get('goal_orientation', 'career')}

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
