import os
import json
from typing import List, Dict, Any
from qdrant_client import models
from app.services.vector_db import QdrantService
from app.services.embedding import BailianEmbeddingService, SparseEmbeddingService
from app.services.reranker import BailianRerankerService

class HybridRetrievalService:
    def __init__(self):
        self.vector_db = QdrantService()
        self.dense_embedding = BailianEmbeddingService()
        self.sparse_embedding = SparseEmbeddingService()
        self.reranker = BailianRerankerService()
        self.parents_dir = os.path.join(os.getcwd(), "data", "parents")
        self.parents_cache = {} # doc_id -> parent_chunks_dict

    def _get_parent_content(self, doc_id: int, parent_id: str) -> str:
        """从本地 JSON 文件中获取大切块内容"""
        if doc_id not in self.parents_cache:
            parent_json_path = os.path.join(self.parents_dir, f"{doc_id}.json")
            if os.path.exists(parent_json_path):
                with open(parent_json_path, "r", encoding="utf-8") as f:
                    self.parents_cache[doc_id] = json.load(f)
            else:
                return ""
        
        return self.parents_cache[doc_id].get(parent_id, "")

    async def search(self, query: str, limit: int = 20, rerank_top_n: int = 5) -> Dict[str, Any]:
        """
        混合检索流程：
        1. 获取查询向量。
        2. 在 Qdrant 中执行混合检索 (Dense + Sparse)，合并获取前 20 条。
        3. 回溯获取对应的大切块内容。
        4. 使用 Reranker 进行二次精排，取前 5 条。
        5. 对前 5 条结果的大切块进行去重，提取最终上下文。
        """
        print(f"开始执行检索: {query}")
        
        # 1. 生成查询向量
        print("正在生成查询向量 (Dense + Sparse)...")
        dense_vec = self.dense_embedding.embed_query(query)
        sparse_vec = self.sparse_embedding.embed_text(query)

        # 2. 执行混合检索 (RRF 融合)
        print(f"正在从 Qdrant 执行混合检索, 候选限制: {limit}...")
        search_result = self.vector_db.client.query_points(
            collection_name=self.vector_db.collection_name,
            prefetch=[
                models.Prefetch(query=dense_vec, using="text-dense", limit=limit),
                models.Prefetch(
                    query=models.SparseVector(indices=sparse_vec["indices"], values=sparse_vec["values"]),
                    using="text-sparse", limit=limit
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )

        # 3. 整理初步检索结果 (Top 20 小切块)
        initial_results = []
        for point in search_result.points:
            initial_results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })

        print(f"混合检索完成, 召回候选点数: {len(initial_results)}")
        if not initial_results:
            print("警告: 未能在向量数据库中找到任何匹配项。")
            return {"final_results": [], "context_chunks": []}

        # 4. 执行多模态重排序 (针对小切块进行精排)
        print(f"正在启动多模态重排序 (模型: {self.reranker.model_name})...")
        reranked_results = self.reranker.rerank(
            query=query,
            documents=initial_results,
            top_n=rerank_top_n
        )
        
        if reranked_results:
            best_score = reranked_results[0].get("rerank_score", 0)
            print(f"重排序完成, Top 1 核心相关度得分: {best_score:.4f}")

        # 5. 仅针对精排后的 Top 5 结果进行大切块回溯与去重
        print("开始父块内容回溯与上下文去重...")
        final_context_chunks = []
        seen_parents = set()
        
        for res in reranked_results:
            payload = res["payload"]
            doc_id = payload.get("doc_id")
            parent_id = payload.get("parent_id")
            
            # 回溯获取大切块全文
            if parent_id:
                parent_text = self._get_parent_content(doc_id, parent_id)
                payload["parent_content"] = parent_text # 补全信息用于前端展示
                
                # 如果这个大切块还没被加入上下文，则加入
                if parent_id not in seen_parents:
                    seen_parents.add(parent_id)
                    final_context_chunks.append({
                        "content": parent_text,
                        "type": payload.get("type"),
                        "heading": payload.get("heading"),
                        "doc_title": payload.get("doc_title")
                    })

        print(f"检索全流程结束。最终提取大切块上下文数量: {len(final_context_chunks)}")
        return {
            "final_results": reranked_results,        # 前 5 个精排后的原信息（含图片路径等）
            "context_chunks": final_context_chunks     # 去重后的 1200 字大切块上下文（喂给 AI）
        }


