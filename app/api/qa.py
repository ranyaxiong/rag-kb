"""
问答API
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.vector_store import VectorStore
from app.core.qa_engine import QAEngine
from app.models.schemas import QuestionRequest, QuestionResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局实例（延迟初始化）
vector_store = None
qa_engine = None

def get_vector_store():
    """获取向量存储实例（延迟初始化）"""
    global vector_store
    if vector_store is None:
        vector_store = VectorStore()
    return vector_store

def get_qa_engine():
    """获取QA引擎实例（延迟初始化）"""
    global qa_engine
    if qa_engine is None:
        qa_engine = QAEngine(get_vector_store())
    return qa_engine


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """智能问答接口"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # 检查是否有文档数据
        collection_info = get_vector_store().get_collection_info()
        if collection_info.get("document_count", 0) == 0:
            return QuestionResponse(
                answer="抱歉，知识库中暂时没有文档。请先上传一些文档后再提问。",
                sources=[],
                processing_time=0.0
            )
        
        # 执行问答
        response = get_qa_engine().ask(
            question=request.question,
            max_sources=request.max_sources
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")


@router.post("/search")
async def search_documents(request: QuestionRequest):
    """文档检索接口（不生成答案）"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # 执行相似度搜索
        relevant_docs = get_qa_engine().get_relevant_documents(
            question=request.question,
            k=request.max_sources or 5
        )
        
        # 处理结果
        results = []
        for doc in relevant_docs:
            result = {
                "document_name": doc.metadata.get("filename", "Unknown"),
                "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                "metadata": {
                    "document_id": doc.metadata.get("document_id"),
                    "chunk_index": doc.metadata.get("chunk_index"),
                    "page": doc.metadata.get("page")
                }
            }
            results.append(result)
        
        return {
            "success": True,
            "query": request.question,
            "results": results,
            "total_found": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/suggestions")
async def get_question_suggestions():
    """获取问题建议"""
    try:
        # 检查是否有文档
        collection_info = get_vector_store().get_collection_info()
        
        if collection_info.get("document_count", 0) == 0:
            return {
                "suggestions": [
                    "请先上传一些文档",
                    "知识库目前为空"
                ]
            }
        
        # 返回一些通用的问题模板
        suggestions = [
            "这个文档讲的是什么？",
            "有什么重要的信息？",
            "能总结一下主要内容吗？",
            "有哪些关键要点？",
            "这个主题的详细说明是什么？"
        ]
        
        return {
            "suggestions": suggestions,
            "document_count": collection_info.get("document_count", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/feedback")
async def submit_feedback(
    question: str,
    answer: str,
    rating: int,  # 1-5
    feedback: Optional[str] = None
):
    """提交用户反馈"""
    try:
        if rating not in range(1, 6):
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # 这里可以将反馈存储到数据库
        # 目前只是记录日志
        logger.info(f"User feedback received - Rating: {rating}, Question: {question[:100]}...")
        
        if feedback:
            logger.info(f"Additional feedback: {feedback}")
        
        return {
            "success": True,
            "message": "Thank you for your feedback!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/health")
async def qa_health_check():
    """问答系统健康检查"""
    try:
        health_info = get_qa_engine().health_check()
        
        return {
            "success": True,
            "health": health_info
        }
        
    except Exception as e:
        logger.error(f"QA health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/stats")
async def get_qa_stats():
    """获取问答系统统计信息"""
    try:
        collection_info = get_vector_store().get_collection_info()
        
        stats = {
            "vector_store": {
                "collection_name": collection_info.get("collection_name"),
                "document_count": collection_info.get("document_count", 0),
                "embedding_model": collection_info.get("embedding_model")
            },
            "qa_settings": {
                "max_sources": qa_engine.vector_store.similarity_threshold,
                "similarity_threshold": vector_store.similarity_threshold,
                "model": "gpt-3.5-turbo"
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting QA stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")