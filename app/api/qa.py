def _extract_overrides_from_headers(request) -> dict:
    """从请求头提取按请求覆盖配置（BYOK）
    支持的请求头：
    - Authorization: "Bearer <API_KEY>" 或直接含 key
    - X-LLM-Provider: openai/deepseek/zhipu/openrouter/custom
    - X-LLM-Base-URL: 自定义兼容 OpenAI 的 API Base URL
    - X-LLM-Model: 聊天模型名称
    """
    overrides = {}
    try:
        # API Key
        auth = request.headers.get("Authorization") or request.headers.get("X-API-Key")
        if auth:
            token = auth.strip()
            if token.lower().startswith("bearer "):
                token = token.split(" ", 1)[1].strip()
            if token:
                overrides["api_key"] = token
        # 其他覆盖项
        provider = request.headers.get("X-LLM-Provider")
        base_url = request.headers.get("X-LLM-Base-URL")
        model = request.headers.get("X-LLM-Model")
        if provider:
            overrides["provider"] = provider
        if base_url:
            overrides["api_base_url"] = base_url
        if model:
            overrides["model"] = model
    except Exception:
        # 安全兜底：出现异常则返回当前累积的 overrides
        pass
    return overrides

"""
问答API
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.vector_store import VectorStore
from app.core.qa_engine import QAEngine
from app.models.schemas import QuestionRequest, QuestionResponse, SourceDocument
from langchain_openai import ChatOpenAI

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
async def ask_question(payload: QuestionRequest, request: Request):
    """智能问答接口"""
    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # 检查是否有文档数据
        collection_info = get_vector_store().get_collection_info()
        if collection_info.get("document_count", 0) == 0:
            return QuestionResponse(
                answer="抱歉，知识库中暂时没有文档。请先上传一些文档后再提问。",
                sources=[],
                processing_time=0.0
            )
        
        # 提取BYOK覆盖，并按需选择引擎
        overrides = _extract_overrides_from_headers(request)
        engine = None
        from app.core.config import settings
        if overrides.get("api_key"):
            # 用户提供了 Key，创建临时引擎（不影响全局实例与测试桩）
            engine = QAEngine(get_vector_store(), overrides=overrides)
        else:
            # 未提供 Key：若全局尚未初始化且也无默认 Key，则走 Demo 回退；
            # 若测试中已用 mock 注入了 qa_engine，则直接复用以保持单测稳定。
            if qa_engine is None and not settings.get_api_key():
                try:
                    k = payload.max_sources or settings.max_sources
                    docs = get_vector_store().similarity_search(payload.question, k=k)
                    sources = []
                    for doc in docs:
                        content = doc.page_content
                        if len(content) > 300:
                            content = content[:300] + "..."
                        sources.append(SourceDocument(
                            document_name=doc.metadata.get("filename", "Unknown"),
                            content=content,
                            similarity_score=1.0,
                            page_number=doc.metadata.get("page")
                        ))
                    return QuestionResponse(
                        answer=(
                            "当前处于 Demo 模式，尚未提供 LLM API Key，因此仅展示检索到的相关内容片段。\n"
                            "请在左侧“模型设置(BYOK)”中填写 API Key 后重试，以生成完整答案。"
                        ),
                        sources=sources,
                        processing_time=0.0
                    )
                except Exception as demo_e:
                    return QuestionResponse(
                        answer=f"当前处于 Demo 模式且未配置 API Key。无法进行生成，仅提示：{str(demo_e)}",
                        sources=[],
                        processing_time=0.0
                    )
            # 使用默认全局引擎（便于单元测试使用 mock）
            engine = get_qa_engine()
        
        # 执行问答
        response = engine.ask(
            question=payload.question,
            max_sources=payload.max_sources
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")


@router.get("/verify-key")
async def verify_key(request: Request):
    """验证 LLM API Key 是否有效（仅做一次最小化调用）"""
    try:
        overrides = _extract_overrides_from_headers(request)
        from app.core.config import settings
        api_key = overrides.get("api_key") or settings.get_api_key()
        if not api_key:
            raise HTTPException(status_code=400, detail="No API key provided. 请在请求头或服务端配置中提供 API Key")
        # 构造模型配置
        model_cfg = settings.get_model_config()
        if overrides.get("provider"):
            model_cfg["provider"] = overrides["provider"]
        if overrides.get("api_base_url"):
            model_cfg["api_base_url"] = overrides["api_base_url"]
        # 模型名可选覆盖
        if overrides.get("model"):
            model_cfg["chat_model"] = overrides["model"]
        # 构建 LLM 客户端并做一次轻量调用
        llm_kwargs = {
            "model": model_cfg["chat_model"],
            "api_key": api_key,
            "temperature": 0.0,
            "max_tokens": 4,
        }
        if model_cfg.get("api_base_url") and model_cfg["api_base_url"] != "https://api.openai.com/v1":
            llm_kwargs["base_url"] = model_cfg["api_base_url"]
            llm_kwargs["organization"] = ""
        llm = ChatOpenAI(**llm_kwargs)
        _ = llm.predict("ping")
        return {"success": True, "provider": model_cfg["provider"], "model": model_cfg["chat_model"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify key failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Verify key failed: {str(e)}")


@router.post("/search")
async def search_documents(payload: QuestionRequest, request: Request):
    """文档检索接口（不生成答案）"""
    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # 选择引擎（当提供 BYOK 时使用临时引擎，否则使用全局，以保持与测试兼容）
        overrides = _extract_overrides_from_headers(request)
        engine = get_qa_engine() if not overrides.get("api_key") else QAEngine(get_vector_store(), overrides=overrides)
        
        # 执行相似度搜索
        relevant_docs = engine.get_relevant_documents(
            question=payload.question,
            k=payload.max_sources or 5
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
            "query": payload.question,
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
        from app.core.config import settings
        collection_info = get_vector_store().get_collection_info()
        
        stats = {
            "vector_store": {
                "collection_name": collection_info.get("collection_name"),
                "document_count": collection_info.get("document_count", 0),
                "embedding_model": collection_info.get("embedding_model")
            },
            "qa_settings": {
                "max_sources": settings.max_sources,
                "similarity_threshold": settings.similarity_threshold,
                "model": settings.chat_model
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting QA stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")