"""
RAG问答引擎模块
"""
import logging
import time
from typing import Dict, List, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from app.core.config import settings
from app.core.vector_store import VectorStore
from app.core.cache_manager import cache_manager
from app.models.schemas import SourceDocument, QuestionResponse

logger = logging.getLogger(__name__)


class QAEngine:
    """RAG问答引擎"""
    
    def __init__(self, vector_store: VectorStore, overrides: Optional[dict] = None):
        self.vector_store = vector_store
        self.llm = None
        self.qa_chain = None
        # 允许按请求覆盖：{"api_key": str, "provider": str, "api_base_url": str, "model": str}
        self._overrides = overrides or {}
        self._effective_model_config = None  # 记录生效的模型配置用于缓存等
        
        self._initialize_llm()
        self._build_qa_chain()
    
    def _initialize_llm(self):
        """初始化大语言模型"""
        try:
            overrides = self._overrides or {}
            # 1) API Key 优先使用请求覆盖，否则使用全局配置
            api_key = overrides.get("api_key") or settings.get_api_key()
            if not api_key:
                raise ValueError(f"API key not configured for {settings.llm_provider}")
            
            # 2) 获取模型配置并应用覆盖项（不修改全局 settings）
            model_config = settings.get_model_config()
            if overrides.get("provider"):
                model_config["provider"] = overrides["provider"]
            if overrides.get("api_base_url"):
                model_config["api_base_url"] = overrides["api_base_url"]
            if overrides.get("model"):
                model_config["chat_model"] = overrides["model"]
            # 记录生效配置
            self._effective_model_config = dict(model_config)
            
            # 使用ChatOpenAI（支持兼容的API）
            llm_kwargs = {
                "model": model_config["chat_model"],
                "api_key": api_key,
                "temperature": 0.1,
                "max_tokens": 1000
            }
            
            # 设置自定义API端点（如果指定）
            if model_config["api_base_url"] and model_config["api_base_url"] != "https://api.openai.com/v1":
                llm_kwargs["base_url"] = model_config["api_base_url"]
                # 对于DeepSeek等兼容OpenAI的API，设置组织ID为空
                llm_kwargs["organization"] = ""
            
            self.llm = ChatOpenAI(**llm_kwargs)
            
            logger.info(f"LLM initialized successfully: {model_config['provider']}/{model_config['chat_model']}")
            
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise
    
    def _build_qa_chain(self, retriever=None):
        """构建问答链"""
        try:
            # 自定义提示模板
            prompt_template = """你是一个智能助手，请根据以下文档内容回答用户的问题。

文档内容：
{context}

问题：{question}

请注意：
1. 请尽量基于提供的文档内容来回答问题
2. 如果文档中没有相关信息，请明确说明
3. 回答要准确、简洁、有帮助
4. 如果涉及多个方面，请分点说明

回答："""
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # 构建检索问答链（支持传入按请求定制的 retriever）
            effective_retriever = retriever or self.vector_store.as_retriever(
                search_kwargs={"k": settings.max_sources}
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=effective_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            # 仅当未传入自定义 retriever 时，保留为默认链
            if retriever is None:
                self.qa_chain = qa_chain
            logger.info("QA chain built successfully")
            return qa_chain
            
        except Exception as e:
            logger.error(f"Error building QA chain: {str(e)}")
            raise
    
    def ask(self, question: str, max_sources: Optional[int] = None, document_id: Optional[str] = None) -> QuestionResponse:
        """回答问题（带缓存优化）"""
        start_time = time.time()
        
        try:
            if not question.strip():
                raise ValueError("Question cannot be empty")
            
            # 使用指定的源文档数量或默认值
            k = max_sources or settings.max_sources
            
            # 首先获取相关文档用于生成上下文hash；若限定文档无命中则回退到全库
            relevant_docs = self.get_relevant_documents(question, k, document_id)
            used_document_id = document_id
            fallback_note = ""
            if document_id and len(relevant_docs) == 0:
                # 回退到全库检索
                logger.info(f"No hits under document_id={document_id}, fallback to global search")
                relevant_docs = self.get_relevant_documents(question, k, None)
                used_document_id = None
                if len(relevant_docs) > 0:
                    fallback_note = "提示：在您选定的文档中未检索到相关内容，已自动在全库中扩大检索范围。"
                else:
                    fallback_note = "提示：在您选定的文档以及全库中均未检索到相关内容。"
            # 基于最终采用的上下文计算hash
            context_hash = cache_manager.get_context_hash(relevant_docs)
            
            # 获取模型配置用于缓存key（使用生效的配置，避免与默认配置混淆）
            model_cfg = self._effective_model_config or settings.get_model_config()
            model_name = f"{model_cfg['provider']}/{model_cfg['chat_model']}"
            
            # 检查QA缓存
            cached_result = cache_manager.get_qa_cache(question, context_hash, model_name)
            if cached_result:
                processing_time = time.time() - start_time
                logger.info(f"Question answered from cache in {processing_time:.2f}s")
                
                return QuestionResponse(
                    answer=cached_result["answer"],
                    sources=[SourceDocument(**src) for src in cached_result["sources"]],
                    processing_time=round(processing_time, 2),
                    from_cache=True
                )
            
            # 缓存未命中，执行RAG查询（为本次请求构建 retriever，防止跨文档混入）
            search_kwargs = {"k": k}
            if used_document_id:
                search_kwargs["filter"] = {"document_id": used_document_id}
            retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)
            logger.info(f"QAEngine.ask using search_kwargs={search_kwargs}")
            qa_chain = self._build_qa_chain(retriever=retriever)
            result = qa_chain({"query": question})
            
            # 处理答案
            answer = result.get("result", "抱歉，我无法找到相关信息来回答这个问题。")
            if fallback_note:
                answer = f"{fallback_note}\n\n" + answer
            source_docs = result.get("source_documents", [])
            # 防御性过滤：若指定了 document_id，确保来源文档仅来自该文档
            if used_document_id:
                before = len(source_docs)
                source_docs = [d for d in source_docs if d.metadata.get("document_id") == used_document_id]
                after = len(source_docs)
                if after < before:
                    logger.info(f"Filtered source documents by document_id={used_document_id}: {before} -> {after}")
            
            # 处理源文档
            sources = self._process_source_documents(source_docs)
            
            # 缓存结果
            sources_dict = [src.dict() for src in sources]
            cache_manager.set_qa_cache(question, context_hash, answer, sources_dict, model_name)
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            response = QuestionResponse(
                answer=answer,
                sources=sources,
                processing_time=round(processing_time, 2),
                from_cache=False
            )
            
            logger.info(f"Question answered successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"抱歉，处理您的问题时发生了错误：{str(e)}"
            
            logger.error(f"Error answering question: {str(e)}")
            
            return QuestionResponse(
                answer=error_msg,
                sources=[],
                processing_time=round(processing_time, 2),
                from_cache=False
            )
    
    def _process_source_documents(self, source_docs: List[Document]) -> List[SourceDocument]:
        """处理源文档信息"""
        sources = []
        
        for doc in source_docs:
            try:
                # 获取文档元数据
                metadata = doc.metadata
                filename = metadata.get('filename', 'Unknown')
                content = doc.page_content
                
                # 截断过长的内容
                if len(content) > 300:
                    content = content[:300] + "..."
                
                source = SourceDocument(
                    document_name=filename,
                    content=content,
                    similarity_score=1.0,  # ChromaDB不直接返回分数，这里使用默认值
                    page_number=metadata.get('page', None)
                )
                
                sources.append(source)
                
            except Exception as e:
                logger.warning(f"Error processing source document: {str(e)}")
                continue
        
        return sources
    
    def get_relevant_documents(
        self, 
        question: str, 
        k: int = None,
        document_id: str = None
    ) -> List[Document]:
        """获取相关文档（不生成答案）"""
        try:
            k = k or settings.max_sources
            
            # 构建过滤条件
            filter_dict = None
            if document_id:
                filter_dict = {"document_id": document_id}
                logger.info(f"Filtering documents by document_id: {document_id}")
            
            relevant_docs = self.vector_store.similarity_search(
                query=question,
                k=k,
                filter_dict=filter_dict
            )
            
            logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error getting relevant documents: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查向量存储
            vector_health = self.vector_store.health_check()
            
            # 测试LLM连接
            test_response = self.llm.predict("Hello")
            
            # 测试完整的QA流程（如果向量存储中有数据）
            collection_info = self.vector_store.get_collection_info()
            qa_test_result = "skipped"
            
            if collection_info.get("document_count", 0) > 0:
                try:
                    test_qa = self.ask("测试问题", max_sources=1)
                    qa_test_result = "working" if test_qa.answer else "failed"
                except:
                    qa_test_result = "failed"
            
            return {
                "status": "healthy",
                "llm": "connected",
                "vector_store": vector_health.get("status", "unknown"),
                "qa_chain": qa_test_result,
                "collection_info": collection_info
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_conversation_context(
        self, 
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """构建对话上下文（为多轮对话预留）"""
        context_parts = []
        
        for turn in conversation_history[-3:]:  # 保留最近3轮对话
            question = turn.get("question", "")
            answer = turn.get("answer", "")
            
            if question and answer:
                context_parts.append(f"Q: {question}")
                context_parts.append(f"A: {answer}")
        
        return "\n".join(context_parts) if context_parts else ""