import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import upload, query, agent_chat
from app.api.v1.endpoints import profile_builder, plan_generator, resource_chat
from app.core.config import settings
import uvicorn

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # 控制台输出
    ]
)
logger = logging.getLogger("main")

app = FastAPI(title="AURA 多模态 RAG + 多智能体学习系统")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册 - 原有 RAG 接口
app.include_router(upload.router, prefix="/api/v1/upload", tags=["上传处理"])
app.include_router(query.router, prefix="/api/v1/query", tags=["检索对话"])

# 路由注册 - 多智能体系统接口
app.include_router(agent_chat.router, prefix="/api/v1/agent", tags=["多智能体对话"])

# 路由注册 - 前端 SSE 接口（与 Vue 前端对齐的 /api/ai/* 路径）
app.include_router(profile_builder.router, prefix="/api/ai/profile", tags=["画像构建"])
app.include_router(plan_generator.router, prefix="/api/ai/plan", tags=["计划生成"])
app.include_router(resource_chat.router, prefix="/api/ai", tags=["资源对话"])

# 挂载静态文件（用于测试 UI）
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "AURA Python 后端服务已启动 (RAG + 多智能体)"}

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("AURA 多智能体学习系统启动")
    logger.info(f"  调试模式: {settings.DEBUG}")
    logger.info(f"  服务端口: {settings.PORT}")
    logger.info(f"  Java 后端: {settings.JAVA_BACKEND_URL}")
    logger.info(f"  Qdrant: {settings.QDRANT_URL}")
    logger.info("=" * 60)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
