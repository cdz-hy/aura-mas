"""
Token 消耗记录工具 - 将 LLM 调用消耗记录到 Java 后端 ai_token_usage 表
"""
import logging
from typing import Optional
from app.services.db.java_client import java_client

logger = logging.getLogger("token_recorder")


def record(
    user_id: int,
    scene: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    task_id: Optional[int] = None,
):
    """记录单次 LLM 调用 token 消耗到 Java 后端"""
    try:
        java_client.record_token_usage(
            user_id=user_id,
            scene=scene,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_id=task_id,
        )
    except Exception as e:
        logger.debug("Token recording failed for scene=%s: %s", scene, e)


def record_from_mimo(llm_client, user_id: int, scene: str, task_id: Optional[int] = None):
    """从 MIMOClient 实例中收集所有 token 记录并写入 Java 后端"""
    records = llm_client.get_usage_records()
    for rec in records:
        record(
            user_id=user_id,
            scene=scene,
            model_name=rec["model"],
            input_tokens=rec["input_tokens"],
            output_tokens=rec["output_tokens"],
            task_id=task_id,
        )
    llm_client.clear_usage_records()
