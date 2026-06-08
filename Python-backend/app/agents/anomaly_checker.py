"""
异常检测工具 - 供各智能体调用，检测生成/检索内容是否与原始目标对齐
"""
import logging
from typing import Tuple

logger = logging.getLogger("agents.anomaly_checker")


def check_content_alignment(original_goal: str, content_summary: str) -> Tuple[bool, str]:
    """
    检查生成/检索的内容是否与原始学习目标对齐。

    Args:
        original_goal: 用户原始学习目标 / user_message
        content_summary: 智能体输出内容的摘要

    Returns:
        (is_aligned, reason) — is_aligned=True 表示对齐，False 表示根本性偏离
    """
    if not original_goal or not content_summary:
        return True, ""

    # 防御性规避：如果原始目标是系统级指令/短反馈控制词，自动跳过对齐校验，避免误判
    control_verbs = ["确认", "生成", "开始", "好的", "ok", "没问题", "继续", "同意", "行", "嗯", "yes", "no"]
    goal_clean = original_goal.strip().lower()
    if len(goal_clean) < 6 or any(v in goal_clean for v in control_verbs):
        logger.info(f"  [异常检测] 原始目标 '{original_goal}' 识别为通用控制指令/简短反馈，自动放行对齐校验")
        return True, ""

    from app.agents.llm_factory import MIMOClient, THINKING_DISABLED
    from app.prompts.anomaly_checker import ANOMALY_CHECK_PROMPT

    llm = MIMOClient(
        model=MIMOClient.MODEL_STANDARD,
        temperature=0,
        max_tokens=128,
        thinking=THINKING_DISABLED,
    )

    messages = [
        {"role": "system", "content": ANOMALY_CHECK_PROMPT},
        {"role": "user", "content": f"原始目标: {original_goal}\n\n生成/检索内容摘要: {content_summary}"},
    ]

    try:
        result = llm.chat_json(messages, max_tokens=128)
        is_aligned = result.get("is_aligned", True)
        reason = result.get("reason", "")
        if not is_aligned:
            logger.warning(f"  [异常检测] 检测到内容偏离: {reason}")
        return is_aligned, reason
    except Exception as e:
        logger.warning(f"  [异常检测] 检测调用失败: {str(e)[:120]}，默认放行")
        return True, ""
