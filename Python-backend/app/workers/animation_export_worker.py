import json
import logging
import tempfile
import threading
from pathlib import Path

import pika

from app.core.config import settings
from app.services.animation_export import QUEUE_NAME, parse_module_data, utc_now
from app.services.db.java_client import java_client
from app.services.qiniu_client import qiniu_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workers.animation_export")
_connection = None
_thread = None


def _save(resource_id: int, module_data: dict) -> None:
    java_client.update_resource_content(resource_id, json.dumps(module_data, ensure_ascii=False))


def process_job(job: dict) -> None:
    resource_id, quality = int(job["resourceId"]), job["quality"]
    resource = java_client.get_resource_by_id(resource_id)
    module_data = parse_module_data(resource)
    state = module_data.setdefault("videoExports", {}).setdefault(quality, {})
    if state.get("resourceVersion") != int(job["resourceVersion"]):
        return
    logger.info("=== 开始处理动画导出任务: 资源ID %s [%s] ===", resource_id, quality)
    try:
        from app.services.animation_renderer import render_animation

        export_temp_dir = Path(__file__).resolve().parent.parent.parent / "temp"
        export_temp_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="aura-export-", dir=export_temp_dir) as directory:
            output = str(Path(directory) / f"animation-{quality}.mp4")
            render_animation(module_data, quality, output)
            
            logger.info("开始上传视频到七牛云...")
            url = qiniu_client.upload_file(output, "animation-video")
            logger.info("上传成功！CDN 地址: %s", url)
            
        state.update({"status": "ready", "url": url, "error": None, "completedAt": utc_now()})
        logger.info("=== 动画导出任务圆满完成: 资源ID %s ===", resource_id)
    except Exception as exc:
        logger.exception("Animation export failed for resource %s", resource_id)
        state.update({"status": "failed", "url": None, "error": str(exc)[:500], "completedAt": utc_now()})
    _save(resource_id, module_data)


def main() -> None:
    global _connection
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
    except Exception as exc:
        logger.warning("RabbitMQ unavailable, animation export worker not started: %s", exc)
        return
    _connection = connection
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        process_job(json.loads(body))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    logger.info("Listening on %s", QUEUE_NAME)
    channel.start_consuming()


def start_background_worker() -> bool:
    """Start the RabbitMQ consumer thread. Returns True if the connection was established."""
    global _thread
    if _thread and _thread.is_alive():
        return True
    _thread = threading.Thread(target=main, name="animation-export-worker", daemon=True)
    _thread.start()
    _thread.join(timeout=3)
    return _thread.is_alive()


def stop_background_worker() -> None:
    connection = _connection
    if connection and connection.is_open:
        try:
            connection.add_callback_threadsafe(connection.close)
        except Exception:
            logger.exception("Failed to stop animation export worker")


if __name__ == "__main__":
    main()
