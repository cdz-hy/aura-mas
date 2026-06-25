from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Dict, Any
import logging
from pydantic import BaseModel
import json

from app.services.db.java_client import JavaBackendClient
from app.graph.knowledge_updater_graph import get_knowledge_updater_graph

router = APIRouter()
logger = logging.getLogger(__name__)
java_client = JavaBackendClient()

class AnalyzeRequest(BaseModel):
    user_id: int
    resource_ids: List[int]

def _reanalyze_resources_task(user_id: int, resource_ids: List[int]):
    updater_graph = get_knowledge_updater_graph()
    
    for resource_id in resource_ids:
        try:
            logger.info(f"后台任务：开始重新分析资源 {resource_id}...")
            # 1. 获取资源信息
            resource = java_client.get_resource_by_id(resource_id)
            if not resource:
                logger.warning(f"后台任务：资源 {resource_id} 不存在")
                continue
            
            # 2. 从 module_data 中提取文本
            module_data = resource.get("moduleData", {})
            if isinstance(module_data, str):
                module_data = json.loads(module_data)
            
            resource_text = ""
            module_type = resource.get("moduleType", "")
            
            if module_type == "document":
                resource_text = module_data.get("content", "") or module_data.get("markdown", "")
            elif module_type == "quiz":
                questions = module_data.get("questions", [])
                resource_text = json.dumps(questions, ensure_ascii=False)
            elif module_type == "summary":
                resource_text = module_data.get("content", "")
            else:
                # 通用回退提取
                resource_text = json.dumps(module_data, ensure_ascii=False)

            if not resource_text or len(str(resource_text)) < 10:
                logger.warning(f"后台任务：资源 {resource_id} 文本太短或提取失败，跳过分析")
                continue

            # 3. 构造 state 并调用图更新
            updater_state = {
                "user_id": user_id,
                "resource_id": resource_id,
                "resource_text": str(resource_text)[:10000] # 防止单次文本过长打爆上下文
            }
            
            updater_graph.invoke(updater_state)
            logger.info(f"后台任务：资源 {resource_id} 分析完成")
            
        except Exception as e:
            logger.error(f"后台任务：重新分析资源 {resource_id} 失败: {e}")

@router.post("/knowledge-graph/analyze")
async def analyze_resources(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    触发对所选资源的重新图谱分析。
    采用异步后台任务防止客户端阻塞。
    """
    if not payload.user_id or not payload.resource_ids:
        raise HTTPException(status_code=400, detail="Missing user_id or resource_ids")
        
    background_tasks.add_task(_reanalyze_resources_task, payload.user_id, payload.resource_ids)
    
    return {"code": 200, "message": "分析任务已投递后台", "data": True}
