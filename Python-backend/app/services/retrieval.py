import os
import json
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from qdrant_client import models
from app.services.vector_db import QdrantService
from app.services.embedding import BailianEmbeddingService, SparseEmbeddingService
from app.services.reranker import BailianRerankerService

# 全局共享线程池，硬性限制最多 15 个并发任务，防止爆 Qps/并发
_executor = ThreadPoolExecutor(max_workers=15)

class HybridRetrievalService:
    def __init__(self):
        self.vector_db = QdrantService()
        self.dense_embedding = BailianEmbeddingService()
        self.sparse_embedding = SparseEmbeddingService()
        self.reranker = BailianRerankerService()
        self.parents_dir = os.path.join(os.getcwd(), "data", "parents")
        self.parents_cache: Dict[int, Dict] = {}  # doc_id -> parent_chunks_dict
        self._cache_max_size = 20  # 最多缓存 20 篇文档，防止长期运行内存泄漏

    def _get_parent_content(self, doc_id: int, parent_id: str) -> str:
        """从本地 JSON 文件中获取大切块内容（带 LRU 上限缓存）"""
        if doc_id not in self.parents_cache:
            # 超出缓存上限时，淘汰最老的条目
            if len(self.parents_cache) >= self._cache_max_size:
                oldest_key = next(iter(self.parents_cache))
                del self.parents_cache[oldest_key]
            parent_json_path = os.path.join(self.parents_dir, f"{doc_id}.json")
            if os.path.exists(parent_json_path):
                with open(parent_json_path, "r", encoding="utf-8") as f:
                    self.parents_cache[doc_id] = json.load(f)
            else:
                return ""
        return self.parents_cache[doc_id].get(parent_id, "")

    async def search(self, query: str, limit: int = 20, rerank_top_n: int = 5, min_rerank_score: float = 0.0, image_bias: float = 0.5) -> Dict[str, Any]:
        """
        混合检索流程：
        1. 获取查询向量。
        2. 在 Qdrant 中执行混合检索 (Dense + Sparse)，合并获取前 20 条。
        3. 回溯获取对应的大切块内容。
        4. 使用 Reranker 进行二次精排，取前 5 条。
        5. 对前 5 条结果的大切块进行去重，提取最终上下文。
        """
        print(f"\n{'='*60}")
        print(f"  [检索启动] 用户查询: {query}")
        print(f"{'='*60}")
        
        loop = asyncio.get_running_loop()

        # 1. 生成查询向量
        print(f"\n  [阶段 1/4] 正在并发生成查询向量 (Dense + Sparse)...")
        dense_task = loop.run_in_executor(_executor, self.dense_embedding.embed_query, query)
        sparse_task = loop.run_in_executor(_executor, self.sparse_embedding.embed_text, query)
        dense_vec, sparse_vec = await asyncio.gather(dense_task, sparse_task)
        print(f"  [阶段 1/4] 查询向量生成完成 (Dense 维度: {len(dense_vec)}, Sparse 非零项: {len(sparse_vec.get('indices', []))})")

        # 2. 并行独立检索 (解决 DBSF 算分不公问题)
        text_limit = max(1, int(limit * (1.0 - image_bias)))
        image_limit = max(1, int(limit * image_bias))
        
        text_filter = models.Filter(must=[models.FieldCondition(key="type", match=models.MatchValue(value="text"))])
        image_filter = models.Filter(must=[models.FieldCondition(key="type", match=models.MatchValue(value="image"))])
        
        # 文本专用检索 (DBSF)
        text_prefetch = [
            models.Prefetch(query=dense_vec, using="text-dense", filter=text_filter, limit=text_limit, score_threshold=0.6)
        ]
        if sparse_vec.get("indices") and len(sparse_vec["indices"]) > 0:
            text_prefetch.append(
                models.Prefetch(
                    query=models.SparseVector(indices=sparse_vec["indices"], values=sparse_vec["values"]),
                    using="text-sparse", filter=text_filter, limit=text_limit, score_threshold=6.0
                )
            )
        else:
            print(f"  [降级] 查询词稀疏向量为空，本次文本检索自动关闭 text-sparse 并联通道")
            
        print(f"\n  [阶段 2/4] 正在执行独立并发检索: 文本(DBSF, 限额 {text_limit}) + 图片(Dense, 限额 {image_limit})...")
        
        text_search_func = partial(
            self.vector_db.client.query_points,
            collection_name=self.vector_db.collection_name,
            prefetch=text_prefetch,
            query=models.FusionQuery(fusion=models.Fusion.DBSF),
            limit=text_limit,
        )

        # 图片专用检索 (Dense Only)
        image_search_func = partial(
            self.vector_db.client.query_points,
            collection_name=self.vector_db.collection_name,
            query=dense_vec,
            using="text-dense",
            query_filter=image_filter,
            limit=image_limit,
            score_threshold=0.5,
        )

        text_result, image_result = await asyncio.gather(
            loop.run_in_executor(_executor, text_search_func),
            loop.run_in_executor(_executor, image_search_func)
        )

        # 3. 整理初步检索结果 (合并)
        initial_results = []
        for point in text_result.points:
            initial_results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })
        for point in image_result.points:
            initial_results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })

        text_recalled = sum(1 for r in initial_results if r["payload"].get("type") == "text")
        image_recalled = sum(1 for r in initial_results if r["payload"].get("type") == "image")
        print(f"  [阶段 2/4] 混合检索完成, 共召回 {len(initial_results)} 个候选 (文本: {text_recalled}, 图片: {image_recalled})")

        if not initial_results:
            print("  [警告] 未能在向量数据库中找到任何匹配项，检索终止。")
            return {"final_results": [], "context_chunks": []}

        # 输出召回阶段的完整日志
        print(f"\n  {'─'*56}")
        print(f"  [召回详情] 以下为 DBSF 融合后的全部 {len(initial_results)} 个候选结果:")
        print(f"  {'─'*56}")
        for idx, res in enumerate(initial_results, 1):
            p = res["payload"]
            doc_type = p.get("type", "unknown")
            dbsf_score = res["score"]
            heading = " > ".join(p.get("heading", [])) if p.get("heading") else "无"
            doc_title = p.get("doc_title", "未知文档")

            if doc_type == "text":
                content_preview = p.get("content", "")[:60].replace("\n", " ")
                print(f"  #{idx:>2} [文本] | DBSF: {dbsf_score:.4f} | 文档: {doc_title} | 章节: {heading}")
                print(f"       内容: {content_preview}...")
            else:
                caption_preview = p.get("image_caption", "无描述")[:50]
                print(f"  #{idx:>2} [图片] | DBSF: {dbsf_score:.4f} | 文档: {doc_title} | 章节: {heading}")
                print(f"       描述: {caption_preview}...")
        print(f"  {'─'*56}")

        # 4. 执行多模态重排序 (针对小切块进行精排)
        print(f"\n  [阶段 3/4] 正在启动多模态重排序 (模型: {self.reranker.model_name}, 精选 Top {rerank_top_n})...")
        rerank_func = partial(
            self.reranker.rerank,
            query=query,
            documents=initial_results,
            top_n=rerank_top_n
        )
        reranked_results = await loop.run_in_executor(_executor, rerank_func)

        # 4.5 过滤低分结果：移除 rerank_score 低于阈值的结果
        if min_rerank_score > 0 and reranked_results:
            before_count = len(reranked_results)
            reranked_results = [r for r in reranked_results if r.get("rerank_score", 0) >= min_rerank_score]
            filtered_count = before_count - len(reranked_results)
            if filtered_count > 0:
                print(f"  [过滤] rerank_score < {min_rerank_score} 的结果已移除: {filtered_count} 条, 剩余 {len(reranked_results)} 条")

        # 5. 仅针对精排后的 Top N 结果进行大切块回溯与去重
        print(f"\n  [阶段 4/4] 开始父块内容回溯与上下文去重...")
        final_context_chunks = []
        seen_parents = set()
        
        for rank, res in enumerate(reranked_results, 1):
            payload = res["payload"]
            doc_id = payload.get("doc_id")
            parent_id = payload.get("parent_id")
            
            # 回溯获取大切块全文
            if parent_id:
                parent_text = self._get_parent_content(doc_id, parent_id)
                # 浅拷贝 payload 避免直接修改原始 Qdrant 返回对象（防止副作用）
                payload = dict(payload)
                payload["parent_content"] = parent_text
                res["payload"] = payload
                
                is_new = parent_id not in seen_parents
                status = "新增" if is_new else "去重跳过"
                parent_preview = parent_text[:40].replace("\n", " ") if parent_text else "空"
                print(f"  [回溯] #{rank} parent_id={parent_id[:8]}... | {status} | 内容: {parent_preview}...")
                
                # 如果这个大切块还没被加入上下文，则加入
                if is_new:
                    seen_parents.add(parent_id)
                    chunk_entry = {
                        "content": parent_text,
                        "type": payload.get("type"),
                        "heading": payload.get("heading"),
                        "doc_title": payload.get("doc_title")
                    }
                    # 图片类型：补充图片 URL 和 AI 描述，供 LLM prompt 引用
                    if payload.get("type") == "image":
                        chunk_entry["image_path"] = payload.get("image_path", "")
                        chunk_entry["image_caption"] = payload.get("image_caption", "")
                    final_context_chunks.append(chunk_entry)

        print(f"\n{'='*60}")
        print(f"  [检索完成] 最终提取去重后大切块上下文: {len(final_context_chunks)} 个")
        print(f"{'='*60}\n")
        return {
            "final_results": reranked_results,        # 前 N 个精排后的原信息（含图片路径等）
            "context_chunks": final_context_chunks     # 去重后的 1200 字大切块上下文（喂给 AI）
        }
