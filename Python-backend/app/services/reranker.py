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
        多模态重排序 (qwen3-vl-rerank)
        API 限制：每个文档对象只能有一种类型的 key (text / image / video)，
        不能在同一个 dict 中同时出现 text 和 image。
        
        图片双通道策略：
        对每张图片，分别生成两个独立的 API 文档条目：
          - {"image": url}     → 让模型直接看图进行视觉匹配
          - {"text": caption}  → 让模型读 AI 描述进行语义匹配
        通过 index_map 记录 API 文档下标 → 原始文档的映射关系，
        取两者中的最高分作为该图片的最终相关性得分。
        """
        if not documents:
            return []

        rerank_docs = []
        # index_map: API文档列表下标 -> 原始 documents 列表下标
        index_map: Dict[int, int] = {}
        text_count = 0
        image_count = 0

        # qwen3-vl-rerank API 硬性限制：image 类型条目最多 6 个
        MAX_IMAGE_ENTRIES = 6
        image_entry_count = 0  # 已使用的 image 条目计数

        for orig_idx, doc in enumerate(documents):
            payload = doc.get("payload", {})
            if payload.get("type") == "text":
                index_map[len(rerank_docs)] = orig_idx
                rerank_docs.append({"text": payload.get("content", "")})
                text_count += 1
            else:
                caption = payload.get("image_caption", "")
                image_url = payload.get("image_path", "")

                if image_url and image_entry_count < MAX_IMAGE_ENTRIES:
                    # 视觉通道：未超出配额，送入图片 URL
                    index_map[len(rerank_docs)] = orig_idx
                    rerank_docs.append({"image": image_url})
                    image_entry_count += 1
                elif image_url and caption:
                    # 超出图片配额：仅用语义描述作为替代（不丢失语义信号）
                    pass  # caption 在下面统一处理

                if caption:
                    # 语义通道：AI 描述始终送入（不受图片配额限制）
                    index_map[len(rerank_docs)] = orig_idx
                    rerank_docs.append({"text": caption})

                if not image_url and not caption:
                    index_map[len(rerank_docs)] = orig_idx
                    rerank_docs.append({"text": "图片内容"})

                image_count += 1

        print(f"  [重排序] 构建文档完成: {text_count} 个文本块, {image_count} 个图片块")
        print(f"  [重排序] 实际送入条目: {len(rerank_docs)} 个 (图片视觉通道: {image_entry_count}/{MAX_IMAGE_ENTRIES}, 其余以语义描述替代)")

        resp = dashscope.TextReRank.call(
            model=self.model_name,
            query={"text": query},
            documents=rerank_docs,
            top_n=min(top_n * 3, len(rerank_docs)),  # 多取一些，去重后再筛 top_n
            api_key=self.api_key
        )

        if resp.status_code == HTTPStatus.OK:
            results = resp.output.results

            # 合并分数：同一原始文档可能有多个 API 条目，取最高分
            score_map: Dict[int, float] = {}  # orig_idx -> best_score
            for res in results:
                orig_idx = index_map.get(res.index)
                if orig_idx is None:
                    continue
                score = res.relevance_score
                if orig_idx not in score_map or score > score_map[orig_idx]:
                    score_map[orig_idx] = score

            # 按最高分排序，筛出 top_n 个原始文档
            sorted_orig_indices = sorted(score_map.keys(), key=lambda i: score_map[i], reverse=True)
            final_results = []
            for orig_idx in sorted_orig_indices[:top_n]:
                doc = documents[orig_idx]
                doc["rerank_score"] = score_map[orig_idx]
                final_results.append(doc)

            # 输出重排序结果摘要日志
            for rank, res in enumerate(final_results, 1):
                p = res["payload"]
                doc_type = p.get("type", "unknown")
                score = res["rerank_score"]
                if doc_type == "text":
                    preview = p.get("content", "")[:40].replace("\n", " ")
                    print(f"  [重排序] #{rank} 文本 | 得分: {score:.4f} | {preview}...")
                else:
                    print(f"  [重排序] #{rank} 图片 | 得分: {score:.4f} | 描述: {p.get('image_caption', '')[:40]}...")

            return final_results
        else:
            raise Exception(f"Reranker API 调用失败 ({resp.status_code}): {resp.message}")
