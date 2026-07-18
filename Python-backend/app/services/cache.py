"""
Redis 缓存工具 — 用户画像缓存层 + 延迟双删 MQ 发布
Redis 不可用时静默降级，不影响主流程
MQ 不可用时跳过延迟删除，仅靠 TTL 兜底
"""
import json
import logging
import redis
import pika
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("services.cache")

_profile_ttl = 300  # 5 分钟
_delay_ms = 2000    # 延迟双删间隔 2 秒

_redis_client: Optional[redis.Redis] = None
_redis_checked = False  # 是否已尝试过连接（无论成功失败，只检查一次）

# ==================== Redis 读写 ====================


def _get_redis() -> Optional[redis.Redis]:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info(f"Redis 连接成功: {settings.REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis 不可用，降级为直连模式: {e}")
        _redis_client = None
        return None


def get_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """从 Redis 读取用户画像缓存，未命中或异常返回 None"""
    r = _get_redis()
    if r is None:
        return None
    try:
        data = r.get(f"aura:profile:{user_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis 读取画像失败: {e}")
    return None


def set_profile(user_id: int, profile: Dict[str, Any], ttl: int = _profile_ttl):
    """将用户画像写入 Redis 缓存"""
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(f"aura:profile:{user_id}", ttl, json.dumps(profile, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Redis 写入画像失败: {e}")


def invalidate_profile(user_id: int):
    """删除用户画像缓存（写入后失效）"""
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(f"aura:profile:{user_id}")
    except Exception as e:
        logger.warning(f"Redis 删除画像缓存失败: {e}")


# ==================== 延迟双删 MQ 发布 ====================

# 延迟队列拓扑（与 cache_consumer.py 一致）
_EXCHANGE = "ai.cache"
_DELAY_QUEUE = "ai.profile.cache.delay"
_TARGET_QUEUE = "ai.profile.cache"
_ROUTING_KEY = "profile.cache"


def publish_delayed_invalidation(user_id: int):
    """发送延迟删除消息到 RabbitMQ，消息 TTL 后由消费者执行第二次删除"""
    try:
        conn = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        ch = conn.channel()

        # 声明交换机和队列（幂等）
        ch.exchange_declare(exchange=_EXCHANGE, durable=True)
        ch.queue_declare(queue=_DELAY_QUEUE, durable=True, arguments={
            "x-message-ttl": _delay_ms,
            "x-dead-letter-exchange": _EXCHANGE,
            "x-dead-letter-routing-key": _ROUTING_KEY,
        })
        ch.queue_declare(queue=_TARGET_QUEUE, durable=True)
        ch.queue_bind(_TARGET_QUEUE, _EXCHANGE, _ROUTING_KEY)

        body = json.dumps({"user_id": user_id})
        ch.basic_publish(
            exchange="",
            routing_key=_DELAY_QUEUE,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        conn.close()
        logger.debug(f"[延迟双删] MQ 消息已发送: user_id={user_id}")
    except Exception as e:
        logger.warning(f"[延迟双删] MQ 发送失败（跳过延迟删除，仅靠 TTL 兜底）: {e}")
