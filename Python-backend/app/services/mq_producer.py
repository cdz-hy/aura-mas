"""
MQ 结果生产者 - 将资源生成结果发送回 Java 后端
"""
import json
import logging
from typing import Optional
import aio_pika
from app.core.config import settings

logger = logging.getLogger("mq.producer")


class MQProducer:
    """向 ai.resource.result 队列发送资源生成结果"""

    EXCHANGE = "ai.exchange"
    ROUTING_KEY_RESULT = "ai.resource.result"

    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None

    async def _ensure_connection(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        if self._channel is None or self._channel.is_closed:
            self._channel = await self._connection.channel()

    async def send_result(
        self,
        task_id: int,
        status: int,
        user_id: int,
        module_data: Optional[str] = None,
        storage_path: Optional[str] = None,
    ):
        """发送资源生成结果到 Java 后端"""
        try:
            await self._ensure_connection()
        except Exception as e:
            logger.warning(f"MQ 不可达，结果将仅落库: {e}")
            return

        message = {
            "taskId": task_id,
            "status": status,
            "userId": user_id,
        }
        if module_data is not None:
            message["moduleData"] = module_data
        if storage_path is not None:
            message["storagePath"] = storage_path

        try:
            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message, ensure_ascii=False).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=self.ROUTING_KEY_RESULT,
            )
            logger.info(f"生成结果已发送至 MQ: taskId={task_id}, status={status}")
        except Exception as e:
            logger.error(f"MQ 结果发送失败: {e}")

    async def close(self):
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


# 全局单例
mq_producer = MQProducer()
