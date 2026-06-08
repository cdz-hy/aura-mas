from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.retrieval import HybridRetrievalService
from app.services.llm import QwenChatService
import json
import asyncio

router = APIRouter()
retrieval_service = HybridRetrievalService()
chat_service = QwenChatService()

class QueryRequest(BaseModel):
    query: str
    limit: int = 20
    rerank_top_n: int = 5

@router.post("/search")
async def search_only(request: QueryRequest):
    """仅检索接口，用于测试召回和重排效果"""
    try:
        results = await retrieval_service.search(
            query=request.query, 
            limit=request.limit, 
            rerank_top_n=request.rerank_top_n
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_with_rag(request: QueryRequest):
    """结合 RAG 的流式对话接口 (SSE)"""
    
    async def event_generator():
        try:
            # 1. 执行检索
            search_data = await retrieval_service.search(
                query=request.query, 
                limit=request.limit, 
                rerank_top_n=request.rerank_top_n
            )
            
            # 2. 先发送检索结果给前端（包含图片和出处）
            yield f"data: {json.dumps({'type': 'search_results', 'data': search_data['final_results']}, ensure_ascii=False)}\n\n"
            
            # 3. 调用 LLM 生成回答
            yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"
            
            # 由于 dashscope 是同步流，我们在线程池中运行它
            loop = asyncio.get_event_loop()
            gen = chat_service.generate_response(request.query, search_data["context_chunks"])
            
            full_content = ""
            while True:
                chunk = await loop.run_in_executor(None, next, gen, None)
                if chunk is None:
                    break
                
                # Qwen 返回的是全量文本，我们需要计算增量（或者前端处理）
                # 这里我们简单处理，假设前端能处理增量
                delta = chunk[len(full_content):]
                full_content = chunk
                if delta:
                    yield f"data: {json.dumps({'type': 'content', 'delta': delta}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
