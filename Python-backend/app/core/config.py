from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 阿里云百炼设置
    DASHSCOPE_API_KEY: str = ""
    QWEN_CHAT_MODEL: str = "qwen-plus"
    QWEN_EMBEDDING_MODEL: str = "qwen3-vl-embedding"
    QWEN_EMBEDDING_URL: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
        "multimodal-embedding/multimodal-embedding"
    )
    QWEN_RERANKER_MODEL: str = "qwen3-vl-rerank"
    QWEN_VL_CHAT_MODEL: str = "qwen3.6-plus"  # 用于图片内容深度分析的对话模型

    # 七牛云 OSS 设置
    QINIU_ACCESS_KEY: str = ""
    QINIU_SECRET_KEY: str = ""
    QINIU_BUCKET_NAME: str = ""
    QINIU_DOMAIN: str = ""

    # Qdrant 向量数据库设置
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "aura_multimodal_resources"
    QDRANT_VECTOR_SIZE: int = 2560  # Qwen3-VL-Embedding 默认维度

    # 小米 MIMO 模型设置 (OpenAI 兼容接口)
    MIMO_API_KEY: str = ""
    MIMO_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"
    MIMO_API_KEY_SPEED: str = ""
    MIMO_BASE_URL_SPEED: str = "https://api.xiaomimimo.com/v1"
    MIMO_MODEL_NAME: str = "mimo-v2.5"
    MIMO_MODEL_PRO_NAME: str = "mimo-v2.5-pro"
    MIMO_MODEL_PRO_SPEED_NAME: str = "mimo-v2.5-pro-ultraspeed"
    MIMO_MODEL_FLASH_NAME: str = "mimo-v2-flash"
    MIMO_CONTEXT_WINDOW: int = 131072

    # MinerU 文档解析 API
    MINERU_API_KEY: str = ""
    MINERU_API_BASE: str = "https://mineru.net/api/v4"

    # Tavily 搜索 API
    TAVILY_API_KEY: str = ""

    # RabbitMQ 设置 (异步任务队列)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Java 后端设置 (多智能体系统数据持久化)
    JAVA_BACKEND_URL: str = "http://localhost:8080"
    JAVA_SERVICE_SECRET: str = "learning-system-internal-service-secret-2024"

    # Redis 缓存设置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 应用基础设置
    DEBUG: bool = True
    PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
