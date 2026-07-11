import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.animation_export import begin_export, normalized_exports, parse_module_data, publish_export
from app.services.db.java_client import java_client
from app.services.animation_narration import narration_is_healthy

router = APIRouter()

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


class ExportRequest(BaseModel):
    quality: str


def _load_animation_resource(resource_id: int) -> tuple[dict, dict]:
    try:
        resource = java_client.get_resource_by_id(resource_id)
    except Exception as exc:
        # #region agent log
        _dbg("D", "animation_export.py:_load_animation_resource", "resource fetch failed", {"resourceId": resource_id, "error": str(exc)[:200]})
        # #endregion
        raise HTTPException(status_code=404, detail="动画资源不存在") from exc
    if resource.get("moduleType") != "animation":
        raise HTTPException(status_code=400, detail="该资源不是动画")
    module_data = parse_module_data(resource)
    narration = module_data.get("narration") or {}
    healthy = narration_is_healthy(narration)
    # #region agent log
    _dbg("D", "animation_export.py:_load_animation_resource", "narration health check", {
        "resourceId": resource_id,
        "healthy": healthy,
        "narrationVersion": narration.get("version"),
        "cueCount": len(narration.get("cues") or []) if isinstance(narration.get("cues"), list) else 0,
        "audioStatus": narration.get("audioStatus"),
        "hasAudioUrl": bool(narration.get("audioUrl")),
    })
    # #endregion
    if not healthy:
        raise HTTPException(status_code=409, detail="动画讲解数据不完整，请重新生成该动画后再导出")
    return resource, module_data


@router.get("/animation/{resource_id}/exports")
async def get_exports(resource_id: int):
    _, module_data = await asyncio.to_thread(_load_animation_resource, resource_id)
    return {"qualities": normalized_exports(module_data)}


@router.post("/animation/{resource_id}/exports")
async def create_export(request: ExportRequest, resource_id: int):
    resource, module_data = await asyncio.to_thread(_load_animation_resource, resource_id)
    version = int(resource.get("version") or 1)
    # #region agent log
    _dbg("A,F", "animation_export.py:create_export", "export requested", {
        "resourceId": resource_id,
        "quality": request.quality,
        "version": version,
        "existingStatus": (module_data.get("videoExports") or {}).get(request.quality, {}).get("status"),
    })
    # #endregion
    try:
        updated, should_publish = begin_export(module_data, request.quality, version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if should_publish:
        await asyncio.to_thread(java_client.update_resource_content, resource_id, json.dumps(updated, ensure_ascii=False))
        try:
            await asyncio.to_thread(publish_export, resource_id, request.quality, version)
            # #region agent log
            _dbg("A", "animation_export.py:create_export", "publish_export ok", {"resourceId": resource_id, "quality": request.quality, "version": version})
            # #endregion
        except Exception as exc:
            # #region agent log
            _dbg("A", "animation_export.py:create_export", "publish_export failed", {"resourceId": resource_id, "error": str(exc)[:300]})
            # #endregion
            state = updated["videoExports"][request.quality]
            state.update({"status": "failed", "error": f"导出队列不可用: {exc}", "completedAt": None})
            await asyncio.to_thread(java_client.update_resource_content, resource_id, json.dumps(updated, ensure_ascii=False))
            raise HTTPException(status_code=503, detail="导出队列暂不可用") from exc
    else:
        # #region agent log
        _dbg("A,F", "animation_export.py:create_export", "publish skipped (cached/in-progress)", {
            "resourceId": resource_id,
            "quality": request.quality,
            "status": updated["videoExports"][request.quality].get("status"),
        })
        # #endregion
    return {"accepted": should_publish, "qualities": normalized_exports(updated)}
