import dashscope
from typing import List, Dict, Any, Optional
from app.core.config import settings
from http import HTTPStatus

class BailianRerankerService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model_name = settings.QWEN_RERANKER_MODEL

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        多模态重排序
        query: 用户查询文本
        documents: 待排序的文档列表，每个元素包含 payload 和 score
        """
        if not documents:
            return []

        # 构造百炼要求的输入格式
        # 注意：这里假设 documents 中的 payload 已经包含了 content 或 image_path (OSS URL)
        rerank_docs = []
        for doc in documents:
            payload = doc.get("payload", {})
            contents = []
            if payload.get("type") == "text":
                # 重排序时直接使用检索到的小切块，保持语义对齐的精准度
                contents.append({"text": payload.get("content", "")})
            else:
                # 对于图片类型，依然使用图片本身进行多模态重排
                contents.append({"image": payload.get("image_path", "")})
            
            rerank_docs.append({"contents": contents})

        resp = dashscope.MultiModalRerank.call(
            model=self.model_name,
            query={"text": query},
            documents=rerank_docs,
            top_n=top_n,
            api_key=self.api_key
        )

        if resp.status_code == HTTPStatus.OK:
            results = resp.output.results
            # 将重排序得分合并回原文档数据
            final_results = []
            for res in results:
                original_doc = documents[res.index]
                original_doc["rerank_score"] = res.relevance_score
                final_results.append(original_doc)
            
            # 按重排序得分从高到低排序
            return sorted(final_results, key=lambda x: x["rerank_score"], reverse=True)
        else:
            raise Exception(f"Reranker API 调用失败 ({resp.status_code}): {resp.message}")
