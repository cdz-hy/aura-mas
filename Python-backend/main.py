import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import upload, query
from app.api.v1.endpoints import profile_builder, plan_generator, resource_chat
from app.api.v1.endpoints import kb
from app.api.v1.endpoints import flashcard
from app.api.v1.endpoints import analytics
from app.api.v1.endpoints import note_agent
from app.core.config import settings
from app.core.reload import get_reload_dirs
from app.services.mq_consumer import mq_consumer
import uvicorn

BASE_DIR = Path(__file__).resolve().parent

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

# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时连接 MQ，关闭时清理"""
    logger.info("=" * 60)
    logger.info("AURA 多智能体学习系统启动")
    logger.info(f"  调试模式: {settings.DEBUG}")
    logger.info(f"  服务端口: {settings.PORT}")
    logger.info(f"  Java 后端: {settings.JAVA_BACKEND_URL}")
    logger.info(f"  Qdrant: {settings.QDRANT_URL}")
    logger.info("=" * 60)

    logger.info("正在启动 MQ 消费者...")
    await mq_consumer.start()

    # 后台保活任务
    keepalive_task = None
    if mq_consumer.running:
        async def keepalive():
            while mq_consumer.running:
                await asyncio.sleep(5)
        keepalive_task = asyncio.create_task(keepalive())

    yield

    # 关闭时清理：先取消保活任务，再关闭连接
    if keepalive_task and not keepalive_task.done():
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass

    await mq_consumer.stop()
    logger.info("MQ 消费者已关闭")


app = FastAPI(title="AURA 多模态 RAG + 多智能体学习系统", lifespan=lifespan)

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

# 路由注册 - 前端 SSE 接口（与 Vue 前端对齐的 /api/ai/* 路径）
app.include_router(profile_builder.router, prefix="/api/ai/profile", tags=["画像构建"])
app.include_router(plan_generator.router, prefix="/api/ai/plan", tags=["计划生成"])
app.include_router(resource_chat.router, prefix="/api/ai", tags=["资源对话"])

# 路由注册 - 知识库管理接口
app.include_router(kb.router, prefix="/api/v1/kb", tags=["知识库管理"])

# 路由注册 - 闪卡生成接口
app.include_router(flashcard.router, prefix="/api/ai", tags=["闪卡生成"])

# 路由注册 - 学习分析接口
app.include_router(analytics.router, prefix="/api/analytics", tags=["学习分析"])

# 路由注册 - 笔记智能整理接口
app.include_router(note_agent.router, prefix="/api/ai", tags=["笔记整理"])

# 挂载静态文件（用于测试 UI）
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
async def root():
    return {"message": "AURA Python 后端服务已启动 (RAG + 多智能体)"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        reload_dirs=get_reload_dirs(BASE_DIR) if settings.DEBUG else None,
    )
