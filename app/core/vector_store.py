"""
向量存储管理模块
"""
import logging
import uuid
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from app.core.config import settings
from app.core.cache_manager import cache_manager
from app.core.cached_embeddings import CachedEmbeddings

logger = logging.getLogger(__name__)


class VectorStore:
    """向量存储管理类（单例模式）"""
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # 只在第一次初始化时设置属性
        if not hasattr(self, 'embeddings'):
            self.embeddings = None
            self.vectorstore = None
            self.chroma_client = None
            self.collection_name = "rag_documents"
            self._initialized = False
    
    def _ensure_initialized(self):
        """确保实例已初始化（延迟初始化）"""
        if not self._initialized:
            self._initialize_embeddings()
            self._initialize_vectorstore()
            self._initialized = True
    
    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        try:
            # 获取嵌入模型的API key
            api_key = settings.get_embedding_api_key()
            if not api_key:
                raise ValueError(f"API key not configured for embedding provider: {settings.embedding_provider}")
            
            # 获取模型配置
            model_config = settings.get_model_config()
            
            # 使用OpenAIEmbeddings（支持兼容的API）
            embedding_kwargs = {
                "api_key": api_key,
                "model": model_config["embedding_model"]
            }
            
            # 设置嵌入模型的API端点
            embedding_api_url = model_config.get("embedding_api_base_url")
            if embedding_api_url and embedding_api_url != "https://api.openai.com/v1":
                embedding_kwargs["base_url"] = embedding_api_url
                # 对于非OpenAI的API，设置组织ID为空
                embedding_kwargs["organization"] = ""
            
            base_embeddings = OpenAIEmbeddings(**embedding_kwargs)
            # 使用缓存包装器
            self.embeddings = CachedEmbeddings(
                base_embeddings=base_embeddings,
                model_name=f"{model_config['embedding_provider']}/{model_config['embedding_model']}"
            )
            
            logger.info(f"Cached embeddings model initialized successfully: {model_config['embedding_provider']}/{model_config['embedding_model']}")
            
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            raise
    
    def _initialize_vectorstore(self):
        """初始化向量存储"""
        try:
            # 配置ChromaDB
            chroma_settings = ChromaSettings(
                persist_directory=settings.chroma_db_path,
                anonymized_telemetry=False
            )
            
            # 使用直接的client_settings方式初始化Langchain的Chroma包装器
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=settings.chroma_db_path,
                client_settings=chroma_settings
            )
            
            # 获取底层的chroma_client用于直接操作
            self.chroma_client = self.vectorstore._client
            
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档到向量存储"""
        self._ensure_initialized()
        try:
            if not documents:
                logger.warning("No documents to add")
                return []
            
            # 为文档生成ID
            doc_ids = []
            for doc in documents:
                if 'chunk_id' not in doc.metadata:
                    doc.metadata['chunk_id'] = str(uuid.uuid4())
                doc_ids.append(doc.metadata['chunk_id'])
            
            # 尝试批量添加
            try:
                self.vectorstore.add_documents(documents, ids=doc_ids)
                self.vectorstore.persist()
                logger.info(f"Added {len(documents)} documents to vector store (batch mode)")
                return doc_ids
            except Exception as batch_error:
                logger.warning(f"Batch processing failed: {str(batch_error)}")
                logger.info("Falling back to individual document processing...")
                
                # 回退到逐个处理模式
                successful_ids = []
                for i, doc in enumerate(documents):
                    try:
                        doc_id = doc_ids[i]
                        self.vectorstore.add_documents([doc], ids=[doc_id])
                        successful_ids.append(doc_id)
                        logger.debug(f"Successfully added document {i+1}/{len(documents)}")
                    except Exception as individual_error:
                        logger.error(f"Failed to add document {i+1}: {str(individual_error)}")
                        continue
                
                # 持久化所有成功的文档
                if successful_ids:
                    self.vectorstore.persist()
                    logger.info(f"Added {len(successful_ids)}/{len(documents)} documents to vector store (individual mode)")
                    return successful_ids
                else:
                    raise Exception("Failed to add any documents to vector store")
                    
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """执行相似度搜索"""
        self._ensure_initialized()
        try:
            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise
    
    def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4,
        filter_dict: Optional[Dict] = None
    ) -> List[tuple]:
        """执行带分数的相似度搜索"""
        self._ensure_initialized()
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # 过滤低于阈值的结果
            filtered_results = [
                (doc, score) for doc, score in results 
                if score >= settings.similarity_threshold
            ]
            
            logger.info(f"Found {len(filtered_results)} relevant documents (threshold: {settings.similarity_threshold})")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in similarity search with score: {str(e)}")
            raise
    
    def delete_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """根据元数据删除文档"""
        self._ensure_initialized()
        try:
            # 获取ChromaDB collection
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # 查找匹配的文档ID
            results = collection.get(where=metadata_filter)
            
            if results and results['ids']:
                # 删除文档
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} documents")
                return True
            else:
                logger.warning("No documents found matching the filter")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
    
    def delete_document_by_id(self, document_id: str) -> bool:
        """根据文档ID删除相关的所有chunks"""
        return self.delete_documents_by_metadata({"document_id": document_id})
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        self._ensure_initialized()
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            count = collection.count()
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": "text-embedding-ada-002"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"error": str(e)}
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """列出所有文档的基本信息"""
        self._ensure_initialized()
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # 获取所有文档的元数据
            results = collection.get(include=['metadatas'])
            
            if not results or not results['metadatas']:
                return []
            
            # 按document_id分组
            documents = {}
            for metadata in results['metadatas']:
                doc_id = metadata.get('document_id', 'unknown')
                filename = metadata.get('filename', 'unknown')
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        'document_id': doc_id,
                        'filename': filename,
                        'chunk_count': 0,
                        'processed_at': metadata.get('processed_at')
                    }
                documents[doc_id]['chunk_count'] += 1
            
            return list(documents.values())
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        self._ensure_initialized()
        try:
            # 检查向量存储连接
            info = self.get_collection_info()
            
            # 测试嵌入模型
            test_embedding = self.embeddings.embed_query("test")
            
            return {
                "status": "healthy",
                "vector_store": "connected",
                "embedding_model": "working",
                "collection_info": info,
                "embedding_dimension": len(test_embedding)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def as_retriever(self, **kwargs):
        """返回LangChain检索器接口"""
        self._ensure_initialized()
        return self.vectorstore.as_retriever(**kwargs)