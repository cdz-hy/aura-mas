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

# 文件校验配置
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".ppt", ".xlsx", ".xls"}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
MAX_PDF_PAGES = 200  # MinerU 单次最大页数


def _validate_file(file: UploadFile) -> None:
    """校验上传文件的类型和大小"""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def _get_pdf_page_count(file_path: str) -> int:
    """获取 PDF 页数"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return len(reader.pages)
    except Exception as e:
        logger.warning("PDF 页数检测失败: %s", e)
        return 0


def _split_pdf(input_path: str, output_dir: str, max_pages: int = MAX_PDF_PAGES) -> list[str]:
    """将 PDF 按最大页数拆分为多个子文件"""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    if total_pages <= max_pages:
        return [input_path]

    parts = []
    for start in range(0, total_pages, max_pages):
        end = min(start + max_pages, total_pages)
        writer = PdfWriter()
        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])

        part_path = os.path.join(output_dir, f"part_{start // max_pages + 1}.pdf")
        with open(part_path, "wb") as f:
            writer.write(f)
        parts.append(part_path)
        logger.info("  [KB拆分] 生成分片: %s (页 %d-%d)", part_path, start + 1, end)

    return parts


def _merge_md_files(md_files: list[str], images_dirs: list[str]) -> tuple[str, str]:
    """合并多个 MinerU 输出的 Markdown 文件和图片目录"""
    import shutil

    merged_content = ""
    merged_images_dir = ""

    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            if merged_content:
                merged_content += "\n\n---\n\n"
            merged_content += content

    # 合并图片目录
    for img_dir in images_dirs:
        if not img_dir or not os.path.exists(img_dir):
            continue
        if not merged_images_dir:
            merged_images_dir = os.path.join(os.path.dirname(md_files[0]), "merged_images")
            os.makedirs(merged_images_dir, exist_ok=True)
        for img_file in Path(img_dir).iterdir():
            if img_file.is_file():
                dest = os.path.join(merged_images_dir, img_file.name)
                if not os.path.exists(dest):
                    shutil.copy2(str(img_file), dest)

    # 写入合并后的 MD 文件
    merged_md_path = os.path.join(os.path.dirname(md_files[0]), "merged.md")
    with open(merged_md_path, "w", encoding="utf-8") as f:
        f.write(merged_content)

    return merged_md_path, merged_images_dir


class KBIngestRequest(BaseModel):
    doc_id: int
    doc_name: str
    file_path: str


async def _ingest_background(doc_id: int, doc_name: str, file_path: str):
    """后台执行文档摄入流程（全异步，不阻塞事件循环）"""
    try:
        # 1. 更新状态为处理中
        await java_client.update_kb_status_async(doc_id, 1)

        # 2. 检查 PDF 页数，超过限制则自动拆分
        ext = Path(file_path).suffix.lower()
        parts_to_process = [file_path]

        if ext == ".pdf":
            page_count = _get_pdf_page_count(file_path)
            if page_count > MAX_PDF_PAGES:
                logger.info(f"  [KB摄入] PDF 页数 {page_count} 超过限制 {MAX_PDF_PAGES}，自动拆分")
                split_dir = f"data/splits/{doc_id}"
                os.makedirs(split_dir, exist_ok=True)
                parts_to_process = _split_pdf(file_path, split_dir, MAX_PDF_PAGES)
                logger.info(f"  [KB摄入] 拆分为 {len(parts_to_process)} 个分片")
            else:
                logger.info(f"  [KB摄入] PDF 页数: {page_count}，无需拆分")

        # 3. 逐个分片调用 MinerU 解析
        all_md_files = []
        all_images_dirs = []

        for part_idx, part_path in enumerate(parts_to_process):
            part_label = f"分片{part_idx + 1}/{len(parts_to_process)}" if len(parts_to_process) > 1 else "全文"
            logger.info(f"  [KB摄入] 开始 MinerU 解析 ({part_label}): doc_id={doc_id}")

            task_id = await mineru_client.create_task(part_path)
            if len(parts_to_process) == 1:
                await java_client.update_kb_status_async(doc_id, 1, mineru_task_id=task_id)

            result = await mineru_client.poll_task(task_id)
            zip_url = result.get("full_zip_url")
            if not zip_url:
                raise Exception(f"MinerU 未返回 zip 下载链接 ({part_label}): result={result}")

            logger.info(f"  [KB摄入] MinerU 解析完成 ({part_label}): doc_id={doc_id}")

            extract_dir = f"data/mineru_output/{doc_id}/{part_idx + 1}"
            md_path, images_dir = await mineru_client.download_and_extract(zip_url, extract_dir)
            all_md_files.append(md_path)
            all_images_dirs.append(images_dir)

        # 4. 合并多个分片的结果
        if len(all_md_files) > 1:
            logger.info(f"  [KB摄入] 合并 {len(all_md_files)} 个分片的 Markdown")
            md_path, images_dir = _merge_md_files(all_md_files, all_images_dirs)
        else:
            md_path = all_md_files[0]
            images_dir = all_images_dirs[0]

        # 5. 读取 MD 内容
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        logger.info(f"  [KB摄入] MD 文件读取完成: doc_id={doc_id}, 内容长度={len(md_content)}")

        # 6. 调用现有处理器进行切片、向量化、入库
        logger.info(f"  [KB摄入] 开始切片入库: doc_id={doc_id}")
        await java_client.update_kb_status_async(doc_id, 4)
        result = await processor.process_document(md_content, doc_id, doc_name, images_dir)
        chunk_count = result.get("chunks_processed", 0)

        # 7. 更新状态为完成
        await java_client.update_kb_status_async(doc_id, 2, chunk_count=chunk_count, collection_name=vector_db.collection_name)
        logger.info(f"  [KB摄入] 完成: doc_id={doc_id}, chunks={chunk_count}, collection={vector_db.collection_name}")

    except Exception as e:
        error_msg = str(e) if e else "未知错误"
        logger.error(f"  [KB摄入] 失败: doc_id={doc_id}, error={error_msg}", exc_info=True)
        try:
            await java_client.update_kb_status_async(doc_id, 3)
        except Exception:
            logger.error(f"  [KB摄入] 状态更新也失败: doc_id={doc_id}")


@router.post("/ingest")
async def ingest_document(
    doc_id: int = Form(...),
    doc_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    接收文件并启动 MinerU 解析流程（异步后台执行）
    """
    # 1. 校验文件类型
    _validate_file(file)

    # 2. 读取并校验文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小 {len(content) / 1024 / 1024:.1f}MB 超过限制 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 3. 保存文件到本地
    file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"  [KB摄入] 文件已保存: {file_path} ({len(content) / 1024:.0f}KB)")

    # 4. 启动后台任务（不等待完成，立即返回）
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
        logger.error("获取集合统计失败: collection=%s error=%s", collection_name, e, exc_info=True)
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
        logger.error("获取文档详情失败: doc_id=%s error=%s", doc_id, e, exc_info=True)
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
        logger.error("删除切片失败: doc_id=%s error=%s", doc_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除切片失败: {str(e)}")
