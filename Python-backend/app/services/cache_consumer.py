"""
缓存失效消费者 — 监听死信队列，执行延迟双删的第二次删除
MQ 拓扑：
  ai.profile.cache.delay (TTL 2s, 死信到 ai.cache 交换机)
    → ai.profile.cache (本消费者监听)
"""
import json
import logging
import asyncio
from typing import Optional
import aio_pika
from app.core.config import settings
from app.services.cache import invalidate_profile

logger = logging.getLogger("mq.cache_consumer")

_EXCHANGE = "ai.cache"
_DELAY_QUEUE = "ai.profile.cache.delay"
_TARGET_QUEUE = "ai.profile.cache"
_ROUTING_KEY = "profile.cache"


class CacheInvalidationConsumer:
    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._consumer_tag: Optional[str] = None
        self._running = False

    async def start(self):
        try:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()

            exchange = await self._channel.declare_exchange(_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)

            # 延迟队列：消息 TTL 后死信到目标队列
            delay_queue = await self._channel.declare_queue(_DELAY_QUEUE, durable=True, arguments={
                "x-message-ttl": 2000,
                "x-dead-letter-exchange": _EXCHANGE,
                "x-dead-letter-routing-key": _ROUTING_KEY,
            })

            # 目标队列：接收过期消息，执行第二次删除
            target_queue = await self._channel.declare_queue(_TARGET_QUEUE, durable=True)
            await target_queue.bind(exchange, _ROUTING_KEY)

            self._consumer_tag = await target_queue.consume(self._on_message)
            self._running = True
            logger.info("缓存失效消费者已启动，监听队列: %s", _TARGET_QUEUE)
        except Exception as e:
            logger.warning("缓存失效消费者启动失败（MQ 可能未就绪）: %s", e)
            self._running = False

    async def _on_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                user_id = body.get("user_id")
                if user_id:
                    invalidate_profile(user_id)
                    logger.info(f"[延迟双删] 第二次缓存删除完成: user_id={user_id}")
            except Exception as e:
                logger.warning(f"[延迟双删] 消息处理失败: {e}")

    async def stop(self):
        if self._consumer_tag and self._channel:
            await self._channel.cancel(self._consumer_tag)
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._running = False


cache_consumer = CacheInvalidationConsumer()
