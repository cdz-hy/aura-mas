from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import upload, query
from app.core.config import settings
import uvicorn

app = FastAPI(title="AURA 多模态 RAG 接口服务")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(upload.router, prefix="/api/v1/upload", tags=["上传处理"])
app.include_router(query.router, prefix="/api/v1/query", tags=["检索对话"])

# 挂载静态文件（用于测试 UI）
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "AURA Python 后端服务已启动"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
