import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.processor import DocumentProcessor

logger = logging.getLogger("api.upload")
router = APIRouter()
processor = DocumentProcessor()

class UploadRequest(BaseModel):
    doc_id: int
    doc_title: str
    md_path: str  # MD 文件的本地绝对路径

@router.post("/process")
async def upload_and_process(request: UploadRequest):
    """
    本地文档处理接口:
    - 传入 MD 文件的本地路径，系统自动读取内容
    - 图片会根据 MD 中的相对路径，在 MD 所在目录下自动查找
    """
    md_path = request.md_path

    if not os.path.exists(md_path):
        raise HTTPException(status_code=400, detail=f"文件不存在: {md_path}")

    md_dir = os.path.dirname(os.path.abspath(md_path))
    logger.info("文档处理请求: title=%s doc_id=%s path=%s", request.doc_title, request.doc_id, md_path)

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        result = await processor.process_document(
            md_content, request.doc_id, request.doc_title, md_dir
        )
        logger.info("文档处理成功: title=%s doc_id=%s", request.doc_title, request.doc_id)
        return result

    except Exception as e:
        logger.error("文档处理失败: title=%s doc_id=%s error=%s", request.doc_title, request.doc_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

