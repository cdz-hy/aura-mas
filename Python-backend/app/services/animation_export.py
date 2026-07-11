import json
from copy import deepcopy
from datetime import datetime, timezone

import pika

from app.core.config import settings

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
