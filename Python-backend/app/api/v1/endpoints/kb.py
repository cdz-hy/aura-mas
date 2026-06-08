"""
知识库管理 API - 文档摄入、Qdrant 查询（全异步）
"""
import os
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.vector_db import QdrantService
from app.services.mineru_client import mineru_client
from app.services.processor import DocumentProcessor
from app.services.db.java_client import java_client

logger = logging.getLogger("api.kb")
router = APIRouter()

# 服务实例
vector_db = QdrantService()
processor = DocumentProcessor()

# 临时文件目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class KBIngestRequest(BaseModel):
    doc_id: int
    doc_name: str
    file_path: str


async def _ingest_background(doc_id: int, doc_name: str, file_path: str):
    """后台执行文档摄入流程（全异步，不阻塞事件循环）"""
    try:
        # 1. 更新状态为处理中
        await java_client.update_kb_status_async(doc_id, 1)

        # 2. 调用 MinerU 解析
        logger.info(f"  [KB摄入] 开始 MinerU 解析: doc_id={doc_id}")
        task_id = await mineru_client.create_task(file_path)
        await java_client.update_kb_status_async(doc_id, 1, mineru_task_id=task_id)

        # 3. 轮询等待完成（异步 sleep，不阻塞事件循环）
        result = await mineru_client.poll_task(task_id)
        zip_url = result.get("full_zip_url")
        if not zip_url:
            raise Exception("MinerU 未返回 zip 下载链接")

        # 4. 下载并解压
        extract_dir = f"data/mineru_output/{doc_id}"
        md_path, images_dir = await mineru_client.download_and_extract(zip_url, extract_dir)

        # 5. 读取 MD 内容
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 6. 调用现有处理器进行切片、向量化、入库
        logger.info(f"  [KB摄入] 开始切片入库: doc_id={doc_id}")
        await java_client.update_kb_status_async(doc_id, 4)
        result = await processor.process_document(md_content, doc_id, doc_name, images_dir)
        chunk_count = result.get("chunks_processed", 0)

        # 7. 更新状态为完成
        await java_client.update_kb_status_async(doc_id, 2, chunk_count=chunk_count, collection_name=vector_db.collection_name)
        logger.info(f"  [KB摄入] 完成: doc_id={doc_id}, chunks={chunk_count}, collection={vector_db.collection_name}")

    except Exception as e:
        logger.error(f"  [KB摄入] 失败: doc_id={doc_id}, error={e}")
        try:
            await java_client.update_kb_status_async(doc_id, 3)
        except Exception:
            pass


@router.post("/ingest")
async def ingest_document(
    doc_id: int = Form(...),
    doc_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    接收文件并启动 MinerU 解析流程（异步后台执行）
    """
    # 保存文件到本地
    file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"  [KB摄入] 文件已保存: {file_path}")

    # 启动后台任务（不等待完成，立即返回）
    asyncio.create_task(_ingest_background(doc_id, doc_name, str(file_path)))

    return {"status": "accepted", "doc_id": doc_id, "message": "文档解析任务已提交"}


@router.post("/reprocess/{doc_id}")
async def reprocess_document(doc_id: int, doc_name: str = Form(...)):
    """
    重新处理文档：
    - 如果本地有 MinerU 解析结果 → 直接切片+向量化（跳过 MinerU）
    - 如果没有 → 从上传目录找原文件，走完整 MinerU 流程
    """
    mineru_dir = Path(f"data/mineru_output/{doc_id}")
    md_files = list(mineru_dir.rglob("*.md")) if mineru_dir.exists() else []

    if md_files:
        # 有本地 MinerU 结果 → 只做切片+向量化
        logger.info(f"  [KB重处理] 发现本地 MinerU 结果，跳过解析: doc_id={doc_id}")

        async def _reprocess_from_local():
            try:
                await java_client.update_kb_status_async(doc_id, 1)

                # 先删除旧的 Qdrant 数据
                vector_db.delete_document_chunks(doc_id)
                logger.info(f"  [KB重处理] 已清除旧向量数据: doc_id={doc_id}")

                md_path = str(md_files[0])
                images_dir = str(mineru_dir / "images")
                if not Path(images_dir).exists():
                    images_dir = ""

                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()

                await java_client.update_kb_status_async(doc_id, 4)
                result = await processor.process_document(md_content, doc_id, doc_name, images_dir)
                chunk_count = result.get("chunks_processed", 0)

                await java_client.update_kb_status_async(doc_id, 2, chunk_count=chunk_count, collection_name=vector_db.collection_name)
                logger.info(f"  [KB重处理] 完成: doc_id={doc_id}, chunks={chunk_count}, collection={vector_db.collection_name}")
            except Exception as e:
                logger.error(f"  [KB重处理] 失败: doc_id={doc_id}, error={e}")
                try:
                    await java_client.update_kb_status_async(doc_id, 3)
                except Exception:
                    pass

        asyncio.create_task(_reprocess_from_local())
        return {"status": "accepted", "doc_id": doc_id, "mode": "local", "message": "从本地结果重新处理"}

    else:
        # 没有本地结果 → 找原文件走完整流程
        import glob
        pattern = f"data/uploads/{doc_id}_*"
        matches = glob.glob(pattern)

        if not matches:
            raise HTTPException(status_code=404, detail=f"未找到 doc_id={doc_id} 的 MinerU 结果或原始文件，无法重处理")

        file_path = matches[0]
        logger.info(f"  [KB重处理] 使用原文件重新解析: {file_path}")

        asyncio.create_task(_ingest_background(doc_id, doc_name, file_path))
        return {"status": "accepted", "doc_id": doc_id, "mode": "full", "message": "重新执行完整 MinerU 解析流程"}


@router.get("/collections/{collection_name}/stats")
async def get_collection_stats(collection_name: str):
    """获取 Qdrant 集合统计信息"""
    try:
        stats = vector_db.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取集合统计失败: {str(e)}")


@router.get("/collections/{collection_name}/documents/{doc_id}/detail")
async def get_document_detail(collection_name: str, doc_id: int):
    """获取指定文档在 Qdrant 中的详细切片信息"""
    try:
        points = vector_db.get_document_chunks(doc_id)

        if not points:
            return {
                "doc_id": doc_id,
                "total_chunks": 0,
                "type_distribution": {},
                "heading_distribution": [],
                "sample_chunks": [],
            }

        # 统计类型分布
        type_dist = {}
        heading_dist = {}
        sample_chunks = []

        for p in points:
            payload = p.payload or {}
            chunk_type = payload.get("type", "unknown")
            type_dist[chunk_type] = type_dist.get(chunk_type, 0) + 1

            # 章节分布
            heading = payload.get("heading", [])
            if heading:
                heading_key = " > ".join(heading) if isinstance(heading, list) else str(heading)
                heading_dist[heading_key] = heading_dist.get(heading_key, 0) + 1

            # 采样前10个切块
            if len(sample_chunks) < 10:
                content = payload.get("content", "")
                sample_chunks.append({
                    "id": str(p.id),
                    "type": chunk_type,
                    "content_preview": content[:200] if content else "",
                    "heading": heading,
                })

        # 章节分布排序
        heading_distribution = [
            {"heading": k, "count": v}
            for k, v in sorted(heading_dist.items(), key=lambda x: -x[1])
        ]

        return {
            "doc_id": doc_id,
            "total_chunks": len(points),
            "type_distribution": type_dist,
            "heading_distribution": heading_distribution[:20],
            "sample_chunks": sample_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")


@router.delete("/collections/{collection_name}/documents/{doc_id}")
async def delete_document_chunks(collection_name: str, doc_id: int):
    """删除指定文档在 Qdrant 中的所有切片"""
    try:
        vector_db.delete_document_chunks(doc_id)

        # 删除本地 parent JSON
        parent_file = Path(f"data/parents/{doc_id}.json")
        if parent_file.exists():
            parent_file.unlink()
            logger.info(f"  [KB] 已删除 parent 文件: {parent_file}")

        return {"status": "success", "doc_id": doc_id, "message": "切片已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除切片失败: {str(e)}")
