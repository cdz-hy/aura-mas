import os
import base64
import logging
import requests
from typing import List, Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("services.embedding")

# 配置 fastembed 模型缓存目录（避免每次启动都下载）
# 优先使用环境变量，否则默认为项目目录下的 .model_cache
CACHE_DIR = os.environ.get("FASTEMBED_CACHE_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".model_cache"
)
os.environ.setdefault("FASTEMBED_CACHE_PATH", CACHE_DIR)

class BailianEmbeddingService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model_name = settings.QWEN_EMBEDDING_MODEL
        self.url = settings.QWEN_EMBEDDING_URL

    def _encode_image(self, image_path: str) -> str:
        """读取本地图片并转换为 Base64 编码"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def embed_query(self, text: str) -> List[float]:
        """纯文本向量化"""
        return self._call_api(text=text)

    def embed_image(self, image_path: str, caption: Optional[str] = None) -> List[float]:
        """图片+描述融合向量化 (Fusion Mode)"""
        return self._call_api(text=caption, image_path=image_path)

    def _call_api(self, text: str = None, image_path: str = None) -> List[float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        contents = []
        if text and text.strip():
            contents.append({"text": text})
        if image_path:
            # 注意：向量化时使用本地路径读取图片并编码
            # 公网 URL 仅存储在元数据中供前端显示
            contents.append({"image": f"data:image/jpeg;base64,{self._encode_image(image_path)}"})
        
        if not contents:
            logger.error("向量化内容为空, 文本和图片至少需要提供一个")
            raise Exception("向量化内容为空, 文本和图片至少需要提供一个")

        payload = {
            "model": self.model_name,
            "input": {"contents": contents},
            "parameters": {
                "enable_fusion": True, # 开启融合模式
                "dimensions": settings.QDRANT_VECTOR_SIZE
            }
        }
        
        resp = requests.post(self.url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            # 兼容 API 返回的不同格式
            if "output" in result and "embedding" in result["output"]:
                return result["output"]["embedding"]
            elif "output" in result and "embeddings" in result["output"]:
                return result["output"]["embeddings"][0]["embedding"]
            else:
                logger.error(f"未知的 API 返回格式: {result}")
                raise Exception(f"未知的 API 返回格式: {result}")
        else:
            logger.error(f"Embedding API 调用失败 ({resp.status_code}): {resp.text}")
            raise Exception(f"Embedding API 调用失败 ({resp.status_code}): {resp.text}")

from fastembed import SparseTextEmbedding

class SparseEmbeddingService:
    def __init__(self):
        # 使用 Qdrant 提供的 BM25 预训练模型
        # fastembed 会自动使用 FASTEMBED_CACHE_PATH 环境变量指定的缓存目录
        self.model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def embed_text(self, text: str) -> Dict[str, Any]:
        """生成文本的稀疏向量 (BM25)"""
        # fastembed 返回的是生成器，取第一个结果
        embeddings = list(self.model.embed([text]))
        embedding = embeddings[0]
        # 转换为 Qdrant 要求的字典格式
        return {
            "indices": embedding.indices.tolist(),
            "values": embedding.values.tolist()
        }
