"""
FastAPI应用入口
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.core.config import settings
from app.api.documents import router as documents_router
from app.api.qa import router as qa_router
from app.api.cost_optimization import router as cost_router
from app.models.schemas import HealthCheck

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("Starting RAG Knowledge Base API...")
    logger.info(f"Upload directory: {settings.upload_dir}")
    logger.info(f"ChromaDB path: {settings.chroma_db_path}")
    
    yield
    
    # 关闭时清理
    logger.info("Shutting down RAG Knowledge Base API...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG知识库API服务",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),  # 从配置中获取允许的域名
    allow_credentials=True,
    allow_methods=settings.get_cors_methods(),  # 限制HTTP方法
    allow_headers=settings.get_cors_headers(),  # 限制请求头
)

# 注册路由
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(qa_router, prefix="/api/qa", tags=["qa"])
app.include_router(cost_router, prefix="/api/cost", tags=["cost"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "RAG Knowledge Base API",
        "version": settings.app_version,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """健康检查端点"""
    try:
        # 检查基本配置
        checks = {
            "openai_api_key": bool(settings.openai_api_key),
            "upload_dir": os.path.exists(settings.upload_dir),
            "chroma_db_path": os.path.exists(settings.chroma_db_path)
        }
        
        # 检查是否所有项都正常
        all_healthy = all(checks.values())
        
        return HealthCheck(
            status="healthy" if all_healthy else "degraded",
            timestamp=datetime.now(),
            version=settings.app_version
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/info")
async def get_info():
    """获取系统信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "max_sources": settings.max_sources,
        "similarity_threshold": settings.similarity_threshold
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )