import os
import shutil
import uuid
import hashlib
import asyncio
import json
import logging
import threading
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from app.services.oss import QiniuOSSService
from app.services.embedding import BailianEmbeddingService, SparseEmbeddingService
from app.services.vector_db import QdrantService
from app.utils.md_parser import parse_markdown
from app.services.ai_analyzer import MultiModalAnalyzer

logger = logging.getLogger("services.processor")

# 入库专属线程池，最大限制 10，防止并发请求过大导致百炼/七牛 API 触发 Rate Limit 报错
_executor = ThreadPoolExecutor(max_workers=10)

class DocumentProcessor:
    def __init__(self):
        self.oss_service = QiniuOSSService()
        self.embedding_service = BailianEmbeddingService()
        self.sparse_embedding_service = SparseEmbeddingService()
        self.ai_analyzer = MultiModalAnalyzer()
        self.vector_db = QdrantService()
        # 确保存储父块 JSON 的目录存在
        self.parents_dir = os.path.join(os.getcwd(), "data", "parents")
        os.makedirs(self.parents_dir, exist_ok=True)
        # 图片 AI 分析缓存及并发锁
        self.cache_lock = threading.Lock()
        self.cache_path = os.path.join(os.getcwd(), "data", "image_caption_cache.json")
        self.image_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with self.cache_lock:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.image_cache, f, ensure_ascii=False, indent=2)

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件的 MD5 哈希值"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def process_document(self, md_content: str, doc_id: int, doc_title: str, image_folder: str) -> Dict[str, Any]:
        """
        文档处理核心流程：
        1. 解析 Markdown 内容，生成小切块和大切块。
        2. 将大切块保存为本地 JSON。
        3. 对图片进行 AI 智能内容分析 (带缓存)。
        4. 分批流式处理小切块并入库向量数据库。
        """
        loop = asyncio.get_running_loop()
        chunks, parent_chunks = parse_markdown(md_content, doc_id, doc_title)
        logger.info(f"解析完成: 提取出 {len(parent_chunks)} 个大切块, {len(chunks)} 个原始切片数据点。")
        
        # 保存大切块到本地 JSON
        parent_json_path = os.path.join(self.parents_dir, f"{doc_id}.json")
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"大切块内容已持久化至: {parent_json_path}")

        processed_points = []
        total = len(chunks)
        skipped = 0
        success_count = 0

        for idx, chunk in enumerate(chunks, 1):
            try:
                dense_vector = []
                sparse_vector = {}
                
                if chunk["type"] == "text":
                    # 跳过空内容的切块
                    if not chunk["content"] or not chunk["content"].strip():
                        logger.info(f"  [{idx}/{total}] 跳过空内容切块。")
                        skipped += 1
                        continue
                    # 处理文本块
                    preview = chunk["content"][:30].replace("\n", " ")
                    logger.info(f"  [{idx}/{total}] 文本块 | 章节: {' > '.join(chunk['heading'])} | 内容: {preview}...")
                    dense_task = loop.run_in_executor(_executor, self.embedding_service.embed_query, chunk["content"])
                    sparse_task = loop.run_in_executor(_executor, self.sparse_embedding_service.embed_text, chunk["content"])
                    dense_vector, sparse_vector = await asyncio.gather(dense_task, sparse_task)
                    payload = chunk.copy()
                    logger.info(f"  [{idx}/{total}] 文本块向量化完成。")
                else:
                    # 处理图片块
                    local_img_path = os.path.join(image_folder, chunk["image_path"])
                    if not os.path.exists(local_img_path):
                        img_name = os.path.basename(chunk["image_path"])
                        local_img_path = os.path.join(image_folder, img_name)

                    if os.path.exists(local_img_path):
                        logger.info(f"  [{idx}/{total}] 图片块 | 文件: {os.path.basename(local_img_path)}")
                        
                        # 0. AI 智能分析图片 (先查缓存)
                        img_hash = self._get_file_hash(local_img_path)
                        with self.cache_lock:
                            ai_caption = self.image_cache.get(img_hash)
                        
                        if ai_caption:
                            logger.info(f"  [{idx}/{total}] 命中图片分析缓存: {ai_caption[:40]}...")
                        else:
                            parent_context = parent_chunks.get(chunk["parent_id"], "")
                            logger.info(f"  [{idx}/{total}] 正在调用 AI 分析图片内容...")
                            ai_caption = await loop.run_in_executor(_executor, self.ai_analyzer.analyze_image, local_img_path, parent_context)
                            if ai_caption:
                                logger.info(f"  [{idx}/{total}] AI 分析完成: {ai_caption[:40]}...")
                                # 更新并保存缓存（移到线程池，避免阻塞事件循环）
                                with self.cache_lock:
                                    self.image_cache[img_hash] = ai_caption
                                await loop.run_in_executor(_executor, self._save_cache)

                        if ai_caption:
                            chunk["image_caption"] = ai_caption
                            parent_chunks[chunk["parent_id"]] = f"AI 图片描述：{ai_caption}"
                        else:
                            logger.warning(f"  [{idx}/{total}] AI 分析返回空，跳过图片。")
                            skipped += 1
                            continue

                        # 1. 上传至七牛云
                        logger.info(f"  [{idx}/{total}] 正在上传图片至七牛云...")
                        file_ext = os.path.splitext(local_img_path)[1]
                        remote_name = f"docs/{doc_id}/{uuid.uuid4()}{file_ext}"
                        try:
                            qiniu_url = await asyncio.wait_for(
                                loop.run_in_executor(_executor, self.oss_service.upload_file, local_img_path, remote_name),
                                timeout=30
                            )
                            logger.info(f"  [{idx}/{total}] 七牛云上传成功: {qiniu_url}")
                        except Exception as e:
                            logger.error(f"  [{idx}/{total}] 七牛云上传失败: {e}, 跳过图片。")
                            skipped += 1
                            continue

                        # 2. 向量化
                        logger.info(f"  [{idx}/{total}] 正在向量化图片...")
                        dense_task = loop.run_in_executor(_executor, self.embedding_service.embed_image, local_img_path, chunk["image_caption"])
                        sparse_task = loop.run_in_executor(_executor, self.sparse_embedding_service.embed_text, chunk["image_caption"])
                        dense_vector, sparse_vector = await asyncio.gather(dense_task, sparse_task)

                        payload = chunk.copy()
                        payload["image_path"] = qiniu_url
                        logger.info(f"  [{idx}/{total}] 图片块向量化完成。")
                    else:
                        logger.warning(f"  [{idx}/{total}] 找不到图片 {local_img_path}, 跳过。")
                        skipped += 1
                        continue

                if dense_vector:
                    vector_dict = {"text-dense": dense_vector}
                    # 护栏：只有 indices 非空时才写入稀疏向量，防止空向量引发 Qdrant OffsetZero 崩溃
                    if sparse_vector and sparse_vector.get("indices") and len(sparse_vector["indices"]) > 0:
                        vector_dict["text-sparse"] = sparse_vector
                    else:
                        logger.warning(f"  [{idx}/{total}] [拦截] 发现空稀疏向量，已丢弃 text-sparse 通道")
                    processed_points.append({
                        "id": chunk["id"],
                        "vector": vector_dict,
                        "payload": payload
                    })

                # 流式同步
                if len(processed_points) >= 20:
                    logger.info(f"[流式同步] 已积累 {len(processed_points)} 个点, 正在执行同步...")
                    await loop.run_in_executor(_executor, self.vector_db.upsert_points, processed_points)
                    success_count += len(processed_points)
                    processed_points = []
                    logger.info(f"  [流式同步] 累计入库数: {success_count}")

            except Exception as e:
                logger.error(f"  [{idx}/{total}] 处理数据块时发生错误: {e}", exc_info=True)
                skipped += 1
                continue

        # 处理剩余零头
        if processed_points:
            logger.info(f"[最终同步] 正在处理剩余 {len(processed_points)} 个点...")
            await loop.run_in_executor(_executor, self.vector_db.upsert_points, processed_points)
            success_count += len(processed_points)
            logger.info(f"  [最终同步] 累计入库数: {success_count}")

        logger.info(f"全部任务结束。最终入库总数: {success_count}, 跳过: {skipped}, 总计: {total}。")

        # 重新写入 Parent JSON
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "chunks_processed": success_count,
            "chunks_skipped": skipped,
            "doc_id": doc_id,
            "parent_json": parent_json_path
        }
