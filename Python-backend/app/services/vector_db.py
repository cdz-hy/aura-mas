import threading
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any

class QdrantService:
    def __init__(self):
        self._local = threading.local()
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()

    @property
    def client(self) -> QdrantClient:
        """动态获取或创建当前线程独享的 Qdrant 客户端，保证多线程并发安全并复用连接池"""
        if not hasattr(self._local, "client"):
            self._local.client = QdrantClient(url=settings.QDRANT_URL)
        return self._local.client

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
        批量插入或更新数据点 (支持自动分批防止 Payload 过大)
        """
        batch_size = 20
        total_points = len(points)
        total_batches = (total_points + batch_size - 1) // batch_size
        
        print(f"开始同步数据至向量库: 总计 {total_points} 个点, 分为 {total_batches} 批次")
        
        for i in range(0, total_points, batch_size):
            batch = points[i : i + batch_size]
            current_batch_num = (i // batch_size) + 1
            
            print(f"  >> 正在推送第 {current_batch_num}/{total_batches} 批次 ({len(batch)} 点)...", end="", flush=True)
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=p['id'],
                            vector=p['vector'],
                            payload=p['payload']
                        ) for p in batch
                    ]
                )
                print(" [成功]")
            except Exception as e:
                print(f" [失败: {e}]")
                raise e
