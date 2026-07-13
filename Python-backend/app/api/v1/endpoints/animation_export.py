import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.animation_export import begin_export, normalized_exports, parse_module_data, publish_or_fallback
from app.services.db.java_client import java_client
from app.services.animation_narration import narration_is_healthy

logger = logging.getLogger("api.animation_export")
router = APIRouter()


class ExportRequest(BaseModel):
    quality: str


def _load_animation_resource(resource_id: int) -> tuple[dict, dict]:
    try:
        resource = java_client.get_resource_by_id(resource_id)
    except Exception as exc:
        logger.error("动画资源加载失败: resourceId=%s error=%s", resource_id, exc)
        raise HTTPException(status_code=404, detail="动画资源不存在") from exc
    if resource.get("moduleType") != "animation":
        raise HTTPException(status_code=400, detail="该资源不是动画")
    module_data = parse_module_data(resource)
    narration = module_data.get("narration") or {}
    healthy = narration_is_healthy(narration)
    if not healthy:
        raise HTTPException(status_code=409, detail="动画讲解数据不完整，请重新生成该动画后再导出")
    return resource, module_data


@router.get("/animation/{resource_id}/exports")
async def get_exports(resource_id: int):
    _, module_data = await asyncio.to_thread(_load_animation_resource, resource_id)
    qualities = normalized_exports(module_data)
    # Auto-recover stale rendering tasks (e.g. server restarted mid-render)
    from app.services.animation_export import is_stale
    for quality, state in qualities.items():
        if state.get("status") == "rendering" and is_stale(state):
            state["status"] = "failed"
            state["error"] = "渲染超时，请重试"
    return {"qualities": qualities}


@router.post("/animation/{resource_id}/exports")
async def create_export(request: ExportRequest, resource_id: int):
    resource, module_data = await asyncio.to_thread(_load_animation_resource, resource_id)
    version = int(resource.get("version") or 1)
    try:
        updated, should_publish = begin_export(module_data, request.quality, version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if should_publish:
        logger.info("动画导出请求: resourceId=%s quality=%s version=%s", resource_id, request.quality, version)
        await asyncio.to_thread(java_client.update_resource_content, resource_id, json.dumps(updated, ensure_ascii=False))
        await asyncio.to_thread(publish_or_fallback, resource_id, request.quality, version)
    else:
        logger.info("动画导出跳过(缓存/进行中): resourceId=%s quality=%s", resource_id, request.quality)
    return {"accepted": should_publish, "qualities": normalized_exports(updated)}
