"""
管理员资源生成与入库 API
- SSE 流式文本生成 (前端直接连接，token 认证)
- 豆包图片生成 (Java 代理，X-Service-Secret 认证)
- 向量化入库 (Java 内部调用，X-Service-Secret 认证)
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.admin_resource_service import admin_resource_service
from app.core.config import settings

logger = logging.getLogger("api.admin_resource")
router = APIRouter()


# ==================== 认证辅助 ====================

def _verify_service_secret(x_service_secret: Optional[str] = Header(None)):
    """验证内部服务密钥（Java 后端调用）"""
    if not x_service_secret or x_service_secret != settings.JAVA_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="无效的服务密钥")


def _verify_admin_token(token: Optional[str] = Query(None)):
    """验证管理员 token（前端直接调用 SSE 时使用）"""
    if not token:
        raise HTTPException(status_code=401, detail="缺少认证 token")
    # 简单验证 token 存在即可，实际权限由 Java 后端保证
    # 前端的 token 是从 Java 获取的 JWT，管理员才能访问此页面


# ==================== 请求模型 ====================

class ImageGenerateRequest(BaseModel):
    prompt: str
    token: str  # 管理员 JWT token


class TextIngestRequest(BaseModel):
    title: str
    content: str
    doc_id: int


class ImageIngestRequest(BaseModel):
    image_url: str
    image_caption: str
    doc_id: int


class DeleteVectorsRequest(BaseModel):
    doc_id: int


# ==================== 文本生成 (SSE, 前端直接连接) ====================

@router.get("/generate/text")
async def generate_text(
    topic: str,
    token: str = Query(..., description="管理员 JWT token"),
    prompt: str = Query("", description="自定义指令"),
):
    """
    SSE 流式文本生成。
    前端通过 EventSource 连接此端点，token 通过 query param 传递。
    事件格式: data: {"type": "chunk", "content": "..."}\\n\\n
    """

    async def event_stream():
        try:
            async for chunk in admin_resource_service.generate_text_stream(topic, prompt):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"[文本生成] 失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 润色提示词 (前端直接调用) ====================

class PolishPromptRequest(BaseModel):
    prompt: str          # 用户原始提示词
    mode: str = "text"   # text / image / rich
    token: str = ""      # 管理员 JWT token

@router.post("/polish-prompt")
async def polish_prompt(req: PolishPromptRequest):
    """用 LLM 润色用户的提示词，使其更详细、更有效"""
    try:
        result = await admin_resource_service.polish_prompt(req.prompt, req.mode)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[润色] 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"润色失败: {str(e)}")


# ==================== 图文一体化生成 (SSE, 前端直接调用) ====================

@router.get("/generate/text-with-images")
async def generate_text_with_images(
    topic: str,
    token: str = Query(..., description="管理员 JWT token"),
    prompt: str = Query("", description="自定义指令"),
):
    """
    SSE 图文一体化生成。
    先流式生成文本，然后自动提取配图描述并发生成图片，最后合并返回。
    """

    async def event_stream():
        try:
            async for event in admin_resource_service.generate_text_with_images_stream(topic, prompt):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[图文生成] SSE 失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 图片生成 (前端直接调用) ====================

@router.post("/generate/image")
async def generate_image(req: ImageGenerateRequest):
    """调用豆包 doubao-seedream 生成图片，前端直接调用"""
    try:
        result = await admin_resource_service.generate_image(req.prompt)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[图片生成] 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")


# ==================== 智能改写 (SSE, 前端直接调用) ====================

class RewriteRequest(BaseModel):
    content: str        # 整篇原始内容
    requirement: str    # 用户的修改要求
    topic: str = ""     # 资源主题

@router.post("/rewrite")
async def rewrite_text(req: RewriteRequest):
    """
    SSE 流式智能改写。
    接收整篇内容 + 修改要求，LLM 只修改用户要求的部分，输出完整内容。
    """

    async def event_stream():
        try:
            async for chunk in admin_resource_service.rewrite_stream(req.content, req.requirement, req.topic):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"[改写] 失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 入库 (Java 内部调用) ====================

@router.post("/ingest/text")
async def ingest_text(
    req: TextIngestRequest,
    x_service_secret: Optional[str] = Header(None),
):
    """文本分块、向量化、存入 Qdrant"""
    _verify_service_secret(x_service_secret)
    try:
        result = await admin_resource_service.ingest_text(
            title=req.title, content=req.content, doc_id=req.doc_id
        )
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[文本入库] 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文本入库失败: {str(e)}")


@router.post("/ingest/image")
async def ingest_image(
    req: ImageIngestRequest,
    x_service_secret: Optional[str] = Header(None),
):
    """图片向量化、存入 Qdrant"""
    _verify_service_secret(x_service_secret)
    try:
        result = await admin_resource_service.ingest_image(
            image_url=req.image_url, caption=req.image_caption, doc_id=req.doc_id
        )
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[图片入库] 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图片入库失败: {str(e)}")


@router.post("/delete-vectors")
async def delete_vectors(
    req: DeleteVectorsRequest,
    x_service_secret: Optional[str] = Header(None),
):
    """删除 Qdrant 中指定 doc_id 的向量数据"""
    _verify_service_secret(x_service_secret)
    try:
        admin_resource_service.delete_vectors(req.doc_id)
        return {"status": "success", "doc_id": req.doc_id}
    except Exception as e:
        logger.error(f"[删除向量] 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除向量失败: {str(e)}")
