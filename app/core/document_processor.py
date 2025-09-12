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
    TextLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings

logger = logging.getLogger(__name__)


class MarkdownLoader:
    """简单的Markdown文档加载器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        """加载markdown文件内容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 创建文档对象
            doc = Document(
                page_content=content,
                metadata={'source': self.file_path}
            )
            
            return [doc]
        except Exception as e:
            logger.error(f"Error loading markdown file {self.file_path}: {str(e)}")
            raise


class WordDocumentLoader:
    """自定义Word文档加载器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        """加载Word文档内容"""
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            
            content = ""
            
            # 检查文件扩展名
            if self.file_path.lower().endswith('.docx'):
                content = self._extract_docx_content()
            elif self.file_path.lower().endswith('.doc'):
                content = self._extract_doc_content()
            else:
                raise ValueError(f"不支持的文件格式: {self.file_path}")
            
            # 创建文档对象
            doc = Document(
                page_content=content,
                metadata={'source': self.file_path}
            )
            
            return [doc]
        except Exception as e:
            logger.error(f"Error loading Word document {self.file_path}: {str(e)}")
            raise
    
    def _extract_docx_content(self) -> str:
        """从docx文件提取文本内容"""
        import zipfile
        import xml.etree.ElementTree as ET
        
        try:
            with zipfile.ZipFile(self.file_path, 'r') as docx:
                # 读取document.xml文件
                document_xml = docx.read('word/document.xml')
                
                # 解析XML
                root = ET.fromstring(document_xml)
                
                # Word文档的命名空间
                namespace = {
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                }
                
                # 提取所有文本节点
                text_elements = root.findall('.//w:t', namespace)
                content = ''.join([elem.text or '' for elem in text_elements])
                
                return content
                
        except Exception as e:
            logger.error(f"Error extracting content from DOCX file: {str(e)}")
            # 如果XML解析失败，尝试使用python-docx作为备选
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(self.file_path)
                return "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                raise ValueError(f"无法解析Word文档，请确保文件格式正确: {str(e)}")
            except Exception as docx_error:
                raise ValueError(f"无法读取Word文档内容: {str(docx_error)}")
    
    def _extract_doc_content(self) -> str:
        """从.doc文件提取文本内容"""
        try:
            # 尝试基础文本提取方法（从二进制中提取可读文本）
            try:
                logger.info("尝试从.doc文件中提取文本内容")
                
                with open(self.file_path, 'rb') as f:
                    raw_content = f.read()
                
                # 方法1：提取连续的可打印字符
                import re
                
                # 查找连续的可打印字符（包括中文Unicode范围）
                # ASCII可打印字符
                ascii_parts = re.findall(rb'[\x20-\x7E]{4,}', raw_content)
                ascii_text = ' '.join([part.decode('ascii', errors='ignore') for part in ascii_parts])
                
                # 尝试UTF-16编码（Word常用）
                utf16_text = ""
                try:
                    # 去除BOM标记并尝试解码
                    if raw_content.startswith(b'\xff\xfe') or raw_content.startswith(b'\xfe\xff'):
                        utf16_text = raw_content[2:].decode('utf-16', errors='ignore')
                    else:
                        utf16_text = raw_content.decode('utf-16le', errors='ignore')
                    
                    # 清理UTF-16文本，去除控制字符
                    utf16_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', utf16_text)
                    utf16_text = ' '.join(utf16_text.split())  # 规范化空白字符
                    
                except Exception as e:
                    logger.debug(f"UTF-16解码失败: {str(e)}")
                
                # 选择最好的结果
                content = ""
                if len(utf16_text.strip()) > len(ascii_text.strip()):
                    content = utf16_text.strip()
                else:
                    content = ascii_text.strip()
                
                # 检查是否提取到有意义的内容
                if content and len(content) >= 10:
                    logger.warning(f"从.doc文件中提取到{len(content)}个字符的内容（可能不完整）")
                    return content
                else:
                    logger.warning("未能从.doc文件中提取到足够的文本内容")
                    
            except Exception as e:
                logger.error(f"文本提取过程中出错: {str(e)}")
            
            # 如果无法提取内容，提供清晰的错误信息和建议
            raise ValueError(
                "❌ 无法处理.doc格式文件\n\n"
                "💡 解决方案：\n"
                "1. 【推荐】使用Microsoft Word打开文件，另存为.docx格式\n"
                "2. 【简单】将文件另存为.txt格式\n"
                "3. 【在线转换】使用在线转换工具将.doc转为.docx\n\n"
                "📋 技术说明：\n"
                ".doc是Microsoft Word 97-2003的二进制格式，需要专门的解析库。\n"
                "系统目前完全支持.docx、.pdf、.txt、.md等格式。"
            )
            
        except ValueError:
            # 重新抛出我们的用户友好错误
            raise
        except Exception as e:
            logger.error(f"Error extracting content from DOC file: {str(e)}")
            raise ValueError(f"处理.doc文件时发生错误: {str(e)}")


class DocumentProcessor:
    """文档处理核心类"""
    
    def __init__(self):
        self.loaders = {
            '.pdf': PyPDFLoader,
            '.docx': WordDocumentLoader,
            '.doc': WordDocumentLoader,
            '.txt': TextLoader,
            '.md': MarkdownLoader
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