import json
import logging
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pika

from app.core.config import settings

logger = logging.getLogger("services.animation_export")

QUEUE_NAME = "ai.animation.export"
QUALITIES = {"1080p": (1920, 1080), "720p": (1280, 720)}
STALE_SECONDS = 30 * 60


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_module_data(resource: dict) -> dict:
    value = resource.get("moduleData") or resource.get("module_data") or {}
    if isinstance(value, str):
        return json.loads(value)
    return deepcopy(value)


def is_stale(state: dict, now: datetime | None = None) -> bool:
    if state.get("status") != "rendering" or not state.get("startedAt"):
        return False
    try:
        started = datetime.fromisoformat(state["startedAt"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    return ((now or datetime.now(timezone.utc)) - started).total_seconds() > STALE_SECONDS


def normalized_exports(module_data: dict) -> dict:
    existing = module_data.get("videoExports") or {}
    return {
        quality: {
            "status": existing.get(quality, {}).get("status", "idle"),
            **existing.get(quality, {}),
        }
        for quality in QUALITIES
    }


def begin_export(module_data: dict, quality: str, resource_version: int) -> tuple[dict, bool]:
    if quality not in QUALITIES:
        raise ValueError("quality must be 1080p or 720p")
    updated = deepcopy(module_data)
    exports = updated.setdefault("videoExports", {})
    current = exports.get(quality, {})
    same_version = current.get("resourceVersion") == resource_version
    if same_version and current.get("status") == "ready" and current.get("url"):
        return updated, False
    if same_version and current.get("status") == "rendering" and not is_stale(current):
        return updated, False
    exports[quality] = {
        "status": "rendering", "startedAt": utc_now(), "completedAt": None,
        "url": None, "error": None, "resourceVersion": resource_version,
    }
    return updated, True


def publish_export(resource_id: int, quality: str, resource_version: int) -> None:
    connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="", routing_key=QUEUE_NAME,
            body=json.dumps({"resourceId": resource_id, "quality": quality, "resourceVersion": resource_version}),
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )
    finally:
        connection.close()


def _fallback_render(resource_id: int, quality: str, resource_version: int) -> None:
    """Render animation in-process when RabbitMQ is unavailable."""
    from app.services.db.java_client import java_client
    from app.services.qiniu_client import qiniu_client

    try:
        resource = java_client.get_resource_by_id(resource_id)
        module_data = parse_module_data(resource)
        state = module_data.setdefault("videoExports", {}).setdefault(quality, {})
        if state.get("resourceVersion") != resource_version:
            return

        from app.services.animation_renderer import render_animation

        with tempfile.TemporaryDirectory(prefix="aura-export-") as directory:
            output = str(Path(directory) / f"animation-{quality}.mp4")
            render_animation(module_data, quality, output)
            url = qiniu_client.upload_file(output, "animation-video")
        state.update({"status": "ready", "url": url, "error": None, "completedAt": utc_now()})
        java_client.update_resource_content(resource_id, json.dumps(module_data, ensure_ascii=False))
    except Exception as exc:
        logger.exception("Fallback export failed for resource %s", resource_id)
        try:
            resource = java_client.get_resource_by_id(resource_id)
            module_data = parse_module_data(resource)
            state = module_data.setdefault("videoExports", {}).setdefault(quality, {})
            state.update({"status": "failed", "url": None, "error": str(exc)[:500], "completedAt": utc_now()})
            java_client.update_resource_content(resource_id, json.dumps(module_data, ensure_ascii=False))
        except Exception:
            logger.exception("Failed to save error state for resource %s", resource_id)


def publish_or_fallback(resource_id: int, quality: str, resource_version: int) -> bool:
    """Try RabbitMQ first; fall back to background thread if unavailable. Returns True if queued via RabbitMQ."""
    try:
        publish_export(resource_id, quality, resource_version)
        return True
    except Exception as exc:
        logger.warning("RabbitMQ unavailable (%s), using fallback renderer for resource %s", exc, resource_id)
        thread = threading.Thread(
            target=_fallback_render,
            args=(resource_id, quality, resource_version),
            name=f"animation-fallback-{resource_id}",
            daemon=True,
        )
        thread.start()
        return False
