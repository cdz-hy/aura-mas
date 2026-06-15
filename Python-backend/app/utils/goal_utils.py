"""
learning_goal 持久化与解析工具

learning_plan.learning_goal 是 JSON 列，存储结构：
{
  "sessions": {
    "<session_id>": {
      "current": "...",        # 该会话当前的学习目标
      "history": [             # 演进历史
        {"goal": "...", "action": "extract|refine|switch", "reasoning": "...", "timestamp": "..."}
      ],
      "updated_at": "..."
    }
  },
  "initial": "..."             # 兼容字段：计划创建时的字符串目标
}
"""
import json
import logging
from typing import Optional

from app.services.db.java_client import java_client

logger = logging.getLogger("utils.goal")


def resolve_session_learning_goal(plan_id: Optional[int], session_id: Optional[str]) -> str:
    """
    从数据库 learning_plan.learning_goal 中读取指定会话的当前学习目标。

    解析顺序（最优先 → 最兜底）：
    1. sessions[session_id].current（会话级目标，最准确）
    2. initial（计划创建时的字符串目标，跨会话兜底）
    3. 空字符串

    任何异常都静默降级到空字符串，不影响主流程。
    """
    if not plan_id or not session_id:
        return ""

    try:
        plan = java_client.get_plan(plan_id)
    except Exception as e:
        logger.debug(f"[goal_utils] 读取 plan {plan_id} 失败: {e}")
        return ""

    raw = plan.get("learningGoal") if isinstance(plan, dict) else None
    if not raw:
        return ""

    # learningGoal 是 JSON 字符串（Java 端 setLearningGoal(toJson(...))）
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        # 不是合法 JSON，按朴素字符串处理
        return raw if isinstance(raw, str) else ""

    if isinstance(parsed, str):
        # 旧格式：直接是字符串
        return parsed
    if isinstance(parsed, dict):
        sessions = parsed.get("sessions") or {}
        session_entry = sessions.get(session_id)
        if isinstance(session_entry, dict):
            current = session_entry.get("current", "")
            if current:
                return current
        # 会话级目标缺失，降级到 initial
        initial = parsed.get("initial", "")
        if isinstance(initial, str) and initial:
            return initial

    return ""
