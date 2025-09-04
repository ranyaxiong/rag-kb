"""
文档处理核心模块
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
import logging

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader, 
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理核心类"""
    
    def __init__(self):
        self.loaders = {
            '.pdf': PyPDFLoader,
            '.docx': UnstructuredWordDocumentLoader,
            '.doc': UnstructuredWordDocumentLoader,
            '.txt': TextLoader,
            '.md': UnstructuredMarkdownLoader
        }
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.supported_extensions = set(self.loaders.keys())
    
    def is_supported_file(self, filename: str) -> bool:
        """检查文件是否支持"""
        _, ext = os.path.splitext(filename.lower())
        return ext in self.supported_extensions
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """保存上传的文件"""
        try:
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            _, ext = os.path.splitext(filename)
            safe_filename = f"{file_id}_{filename}"
            
            # 创建日期目录
            date_dir = datetime.now().strftime("%Y-%m-%d")
            full_dir = os.path.join(settings.upload_dir, date_dir)
            os.makedirs(full_dir, exist_ok=True)
            
            file_path = os.path.join(full_dir, safe_filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file {filename}: {str(e)}")
            raise
    
    def load_document(self, file_path: str) -> List[Document]:
        """加载文档内容"""
        try:
            _, ext = os.path.splitext(file_path.lower())
            
            if ext not in self.loaders:
                raise ValueError(f"Unsupported file type: {ext}")
            
            loader_class = self.loaders[ext]
            loader = loader_class(file_path)
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} document(s) from {file_path}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割文档为块"""
        try:
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # 添加块索引到元数据
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['chunk_id'] = str(uuid.uuid4())
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting documents: {str(e)}")
            raise
    
    def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """处理单个文档的完整流程"""
        try:
            doc_id = str(uuid.uuid4())
            
            # 加载文档
            documents = self.load_document(file_path)
            
            # 添加文档元数据
            for doc in documents:
                doc.metadata.update({
                    'document_id': doc_id,
                    'filename': filename,
                    'file_path': file_path,
                    'processed_at': datetime.now().isoformat()
                })
            
            # 分割文档
            chunks = self.split_documents(documents)
            
            result = {
                'document_id': doc_id,
                'filename': filename,
                'file_path': file_path,
                'chunks': chunks,
                'chunk_count': len(chunks),
                'status': 'completed'
            }
            
            logger.info(f"Successfully processed document: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            return {
                'document_id': str(uuid.uuid4()),
                'filename': filename,
                'file_path': file_path,
                'chunks': [],
                'chunk_count': 0,
                'status': 'failed',
                'error_message': str(e)
            }
    
    def get_document_info(self, file_path: str) -> Dict[str, Any]:
        """获取文档基本信息"""
        try:
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            _, ext = os.path.splitext(filename)
            
            return {
                'filename': filename,
                'file_type': ext.lower(),
                'file_size': stat.st_size,
                'upload_time': datetime.fromtimestamp(stat.st_mtime),
                'is_supported': self.is_supported_file(filename)
            }
        except Exception as e:
            logger.error(f"Error getting document info for {file_path}: {str(e)}")
            return None