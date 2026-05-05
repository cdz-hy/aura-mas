from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any

class QdrantService:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        """确保 Qdrant 集合存在，不存在则创建"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            # 配置混合检索：Dense (Qwen) + Sparse (BM25)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "text-dense": models.VectorParams(size=settings.QDRANT_VECTOR_SIZE, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "text-sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=True)
                    )
                }
            )

    def upsert_points(self, points: List[Dict[str, Any]]):
        """
        批量插入或更新数据点
        points 列表中的每个 dict 应包含:
        - id: str/int (UUID)
        - vector: dict {"text-dense": [...], "text-sparse": {...}}
        - payload: dict (元数据)
        """
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=p['id'],
                    vector=p['vector'],
                    payload=p['payload']
                ) for p in points
            ]
        )
