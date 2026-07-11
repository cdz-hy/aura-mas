import json
import logging
import tempfile
import threading
import time
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

# #region agent log
_DEBUG_LOG = Path(r"D:\a\Aura\aura-mas-develop\debug-55a441.log")

def _dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    try:
        payload = {
            "sessionId": "55a441",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion


def _save(resource_id: int, module_data: dict) -> None:
    java_client.update_resource_content(resource_id, json.dumps(module_data, ensure_ascii=False))


def process_job(job: dict) -> None:
    resource_id, quality = int(job["resourceId"]), job["quality"]
    # #region agent log
    _dbg("A,F", "animation_export_worker.py:process_job", "job received", {
        "resourceId": resource_id,
        "quality": quality,
        "jobVersion": job.get("resourceVersion"),
    })
    # #endregion
    resource = java_client.get_resource_by_id(resource_id)
    module_data = parse_module_data(resource)
    state = module_data.setdefault("videoExports", {}).setdefault(quality, {})
    if state.get("resourceVersion") != int(job["resourceVersion"]):
        # #region agent log
        _dbg("F", "animation_export_worker.py:process_job", "version mismatch skip", {
            "resourceId": resource_id,
            "stateVersion": state.get("resourceVersion"),
            "jobVersion": job.get("resourceVersion"),
            "stateStatus": state.get("status"),
        })
        # #endregion
        return
    try:
        from app.services.animation_renderer import dependency_status, render_animation

        # #region agent log
        _dbg("B", "animation_export_worker.py:process_job", "dependency status", dependency_status())
        # #endregion
        with tempfile.TemporaryDirectory(prefix="aura-export-") as directory:
            output = str(Path(directory) / f"animation-{quality}.mp4")
            render_animation(module_data, quality, output)
            # #region agent log
            _dbg("C", "animation_export_worker.py:process_job", "render_animation ok", {
                "resourceId": resource_id,
                "outputExists": Path(output).exists(),
                "outputBytes": Path(output).stat().st_size if Path(output).exists() else 0,
            })
            # #endregion
            url = qiniu_client.upload_file(output, "animation-video")
        # #region agent log
        _dbg("E", "animation_export_worker.py:process_job", "upload ok", {"resourceId": resource_id, "urlHost": url.split("/")[2] if "://" in url else None})
        # #endregion
        state.update({"status": "ready", "url": url, "error": None, "completedAt": utc_now()})
    except Exception as exc:
        # #region agent log
        _dbg("B,C,E", "animation_export_worker.py:process_job", "export failed", {
            "resourceId": resource_id,
            "errorType": type(exc).__name__,
            "error": str(exc)[:500],
        })
        # #endregion
        logger.exception("Animation export failed for resource %s", resource_id)
        state.update({"status": "failed", "url": None, "error": str(exc)[:500], "completedAt": utc_now()})
    _save(resource_id, module_data)


def main() -> None:
    global _connection
    connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
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


def start_background_worker() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=main, name="animation-export-worker", daemon=True)
    _thread.start()


def stop_background_worker() -> None:
    connection = _connection
    if connection and connection.is_open:
        try:
            connection.add_callback_threadsafe(connection.close)
        except Exception:
            logger.exception("Failed to stop animation export worker")


if __name__ == "__main__":
    main()
