"""
数据模型定义
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str
    file_type: str
    file_size: int


class DocumentCreate(DocumentBase):
    """文档创建模型"""
    pass


class Document(DocumentBase):
    """文档响应模型"""
    id: str
    upload_time: datetime
    status: str  # "processing", "completed", "failed"
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None


class DocumentChunk(BaseModel):
    """文档块模型"""
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict


class QuestionRequest(BaseModel):
    """问答请求模型"""
    question: str
    max_sources: Optional[int] = 3


class SourceDocument(BaseModel):
    """来源文档模型"""
    document_name: str
    content: str
    similarity_score: float
    page_number: Optional[int] = None


class QuestionResponse(BaseModel):
    """问答响应模型"""
    answer: str
    sources: List[SourceDocument]
    processing_time: float


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None


class HealthCheck(BaseModel):
    """健康检查模型"""
    status: str = "healthy"
    timestamp: datetime = datetime.now()
    version: str