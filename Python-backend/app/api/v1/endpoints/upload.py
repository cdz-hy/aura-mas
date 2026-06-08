from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from app.services.processor import DocumentProcessor

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
    
    # 校验文件是否存在
    if not os.path.exists(md_path):
        raise HTTPException(status_code=400, detail=f"文件不存在: {md_path}")
    
    # MD 文件所在的目录，作为图片的查找基准路径
    md_dir = os.path.dirname(os.path.abspath(md_path))
    
    print(f"收到上传请求: {request.doc_title} (ID: {request.doc_id})")
    print(f"MD 文件路径: {md_path}")
    print(f"图片查找基准目录: {md_dir}")

    try:
        # 读取 MD 文件内容
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 执行核心处理逻辑，图片目录就是 MD 文件所在的目录
        result = await processor.process_document(
            md_content, request.doc_id, request.doc_title, md_dir
        )
        print(f"文档 {request.doc_title} 处理成功。")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

