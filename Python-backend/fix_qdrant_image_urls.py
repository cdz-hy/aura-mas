import sys
import os

# 将当前目录添加到 PYTHONPATH 以便能导入 app 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.vector_db import QdrantService
from qdrant_client.http import models

def fix_image_urls():
    print("开始修复 Qdrant 中的图片 URL...")
    qdrant = QdrantService()
    client = qdrant.client
    collection_name = qdrant.collection_name
    
    old_domain = "te38fyk81.hn-bkt.clouddn.com"
    new_domain = "img.cdzhy.top"
    
    offset = None
    batch_size = 100
    updated_count = 0
    total_checked = 0
    
    while True:
        # 滚动获取数据库中的点（仅获取 Payload，不获取向量以节省内存）
        result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points, next_offset = result
        if not points:
            break
            
        for point in points:
            total_checked += 1
            payload = point.payload
            
            # 检查是否有 image_path 字段且包含旧域名
            if payload and "image_path" in payload:
                url = payload.get("image_path", "")
                if old_domain in url:
                    new_url = url.replace(old_domain, new_domain)
                    
                    # 仅覆盖更新指定的 payload 字段，不影响其他 payload 和向量
                    client.set_payload(
                        collection_name=collection_name,
                        payload={"image_path": new_url},
                        points=[point.id]
                    )
                    updated_count += 1
            
        print(f"已扫描 {total_checked} 个切块，已更新 {updated_count} 个图片链接...")
        
        if next_offset is None:
            break
        offset = next_offset
        
    print(f"\n修复完成！共扫描 {total_checked} 个数据点，成功更新 {updated_count} 个图片的域名。")

if __name__ == "__main__":
    fix_image_urls()
