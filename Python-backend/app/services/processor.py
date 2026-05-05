import os
import shutil
import uuid
from typing import List, Dict, Any
from app.services.oss import QiniuOSSService
from app.services.embedding import BailianEmbeddingService, SparseEmbeddingService
from app.services.vector_db import QdrantService
from app.utils.md_parser import parse_markdown
from app.services.ai_analyzer import MultiModalAnalyzer
import json

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

    async def process_document(self, md_content: str, doc_id: int, doc_title: str, image_folder: str) -> Dict[str, Any]:
        """
        文档处理核心流程：
        1. 解析 Markdown 内容，生成小切块和大切块。
        2. 将大切块保存为本地 JSON。
        3. 对图片进行 AI 智能内容分析，生成高质量 Caption。
        4. 处理小切块并入库向量数据库。
        """
        chunks, parent_chunks = parse_markdown(md_content, doc_id, doc_title)
        print(f"解析完成: 提取出 {len(parent_chunks)} 个大切块, {len(chunks)} 个原始切片数据点。")
        
        # 保存大切块到本地 JSON
        parent_json_path = os.path.join(self.parents_dir, f"{doc_id}.json")
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        print(f"大切块内容已持久化至: {parent_json_path}")

        processed_points = []
        total = len(chunks)
        skipped = 0
        for idx, chunk in enumerate(chunks, 1):
            try:
                dense_vector = []
                sparse_vector = {}
                
                if chunk["type"] == "text":
                    # 跳过空内容的切块
                    if not chunk["content"] or not chunk["content"].strip():
                        print(f"  [{idx}/{total}] 跳过空内容切块。")
                        skipped += 1
                        continue
                    # 处理文本块
                    preview = chunk["content"][:30].replace("\n", " ")
                    print(f"  [{idx}/{total}] 文本块 | 章节: {' > '.join(chunk['heading'])} | 内容: {preview}...")
                    dense_vector = self.embedding_service.embed_query(chunk["content"])
                    sparse_vector = self.sparse_embedding_service.embed_text(chunk["content"])
                    payload = chunk.copy()
                    print(f"  [{idx}/{total}] 文本块向量化完成。")
                else:
                    # 处理图片块
                    local_img_path = os.path.join(image_folder, chunk["image_path"])
                    if not os.path.exists(local_img_path):
                        img_name = os.path.basename(chunk["image_path"])
                        local_img_path = os.path.join(image_folder, img_name)

                    if os.path.exists(local_img_path):
                        print(f"  [{idx}/{total}] 图片块 | 文件: {os.path.basename(local_img_path)}")
                        # 0. AI 智能分析图片并更新 Caption
                        parent_context = parent_chunks.get(chunk["parent_id"], "")
                        print(f"  [{idx}/{total}] 正在调用 AI 分析图片内容...")
                        ai_caption = self.ai_analyzer.analyze_image(local_img_path, parent_context)
                        if ai_caption:
                            print(f"  [{idx}/{total}] AI 分析完成: {ai_caption[:40]}...")
                            chunk["image_caption"] = ai_caption
                            # 同步更新对应存储在 JSON 里的 parent 内容（图片描述部分）
                            parent_chunks[chunk["parent_id"]] = f"AI 图片描述：{ai_caption}"

                        # 1. 上传至七牛云
                        print(f"  [{idx}/{total}] 正在上传图片至七牛云...")
                        file_ext = os.path.splitext(local_img_path)[1]
                        remote_name = f"docs/{doc_id}/{uuid.uuid4()}{file_ext}"
                        qiniu_url = self.oss_service.upload_file(local_img_path, remote_name)
                        print(f"  [{idx}/{total}] 七牛云上传成功: {qiniu_url}")
                        
                        # 2. 向量化 (使用 AI 生成的更精准 Caption)
                        dense_vector = self.embedding_service.embed_image(local_img_path, chunk["image_caption"])
                        sparse_vector = self.sparse_embedding_service.embed_text(chunk["image_caption"])
                        
                        payload = chunk.copy()
                        payload["image_path"] = qiniu_url
                        print(f"  [{idx}/{total}] 图片块向量化完成。")
                    else:
                        print(f"  [{idx}/{total}] 警告: 找不到图片 {local_img_path}, 跳过。")
                        skipped += 1
                        continue

                if dense_vector:
                    processed_points.append({
                        "id": chunk["id"],
                        "vector": {
                            "text-dense": dense_vector,
                            "text-sparse": sparse_vector
                        },
                        "payload": payload
                    })
            except Exception as e:
                print(f"  [{idx}/{total}] 处理数据块时发生错误: {e}")
                skipped += 1
                continue

        print(f"全部切块处理完毕。成功: {len(processed_points)}, 跳过: {skipped}, 总计: {total}。")

        # 批量存入向量数据库
        if processed_points:
            print(f"正在同步 {len(processed_points)} 个数据点至 Qdrant 向量数据库...")
            self.vector_db.upsert_points(processed_points)
            print("Qdrant 同步完成。")

        # 图片分析后 JSON 可能有更新, 重新写入
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "chunks_processed": len(processed_points),
            "chunks_skipped": skipped,
            "doc_id": doc_id,
            "parent_json": parent_json_path
        }
