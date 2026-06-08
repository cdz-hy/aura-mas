import os
import base64
import requests
from typing import List, Optional, Dict, Any
from app.core.config import settings

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
                raise Exception(f"未知的 API 返回格式: {result}")
        else:
            raise Exception(f"Embedding API 调用失败 ({resp.status_code}): {resp.text}")

import logging

logger = logging.getLogger("services.embedding")

# fastembed 延迟导入，避免 HuggingFace 下载在模块 import 阶段卡死 FastAPI 启动
SparseTextEmbedding = None  # type: ignore


def _get_sparse_embedding_model():
    """懒加载 BM25 稀疏向量模型，失败时返回 None 并降级"""
    global SparseTextEmbedding
    if SparseTextEmbedding is not None:
        return SparseTextEmbedding

    try:
        from fastembed import SparseTextEmbedding as _SparseTextEmbedding
        SparseTextEmbedding = _SparseTextEmbedding
        return SparseTextEmbedding
    except Exception as e:
        logger.error(f"fastembed 模型加载失败 (非致命): {e}")
        return None


class SparseEmbeddingService:
    def __init__(self):
        # 模型延迟到首次调用时加载，不在 import 阶段触发 HuggingFace 下载
        self._model = None
        self._model_load_failed = False

    @property
    def model(self):
        if self._model is not None:
            return self._model
        if self._model_load_failed:
            return None

        _SparseTextEmbedding = _get_sparse_embedding_model()
        if _SparseTextEmbedding is None:
            self._model_load_failed = True
            return None

        try:
            self._model = _SparseTextEmbedding(model_name="Qdrant/bm25")
            logger.info("BM25 稀疏向量模型已加载")
            return self._model
        except Exception as e:
            self._model_load_failed = True
            logger.error(f"BM25 模型初始化失败 (非致命，将降级为仅稠密检索): {e}")
            return None

    def embed_text(self, text: str) -> Dict[str, Any]:
        """生成文本的稀疏向量 (BM25)，加载失败时返回空向量"""
        m = self.model
        if m is None:
            logger.warning("BM25 模型不可用，返回空稀疏向量")
            return {"indices": [], "values": []}
        embeddings = list(m.embed([text]))
        embedding = embeddings[0]
        return {
            "indices": embedding.indices.tolist(),
            "values": embedding.values.tolist()
        }
