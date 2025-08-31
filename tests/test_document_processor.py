"""
文档处理器测试
"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from app.core.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """文档处理器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.processor = DocumentProcessor()
    
    def test_supported_file_extensions(self):
        """测试支持的文件格式"""
        assert self.processor.is_supported_file("test.pdf")
        assert self.processor.is_supported_file("test.docx")
        assert self.processor.is_supported_file("test.txt")
        assert self.processor.is_supported_file("test.md")
        assert not self.processor.is_supported_file("test.xlsx")
        assert not self.processor.is_supported_file("test.jpg")
    
    def test_save_uploaded_file(self):
        """测试文件保存功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟设置
            with patch('app.core.document_processor.settings') as mock_settings:
                mock_settings.upload_dir = temp_dir
                
                # 测试保存文件
                content = b"test content"
                filename = "test.txt"
                
                file_path = self.processor.save_uploaded_file(content, filename)
                
                # 验证文件是否保存成功
                assert os.path.exists(file_path)
                assert filename in os.path.basename(file_path)
                
                # 验证文件内容
                with open(file_path, 'rb') as f:
                    saved_content = f.read()
                assert saved_content == content
    
    def test_get_document_info(self):
        """测试获取文档信息"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            info = self.processor.get_document_info(temp_file_path)
            
            assert info is not None
            assert info['filename'] == os.path.basename(temp_file_path)
            assert info['file_type'] == '.txt'
            assert info['file_size'] > 0
            assert info['is_supported'] is True
            
        finally:
            os.unlink(temp_file_path)
    
    @patch('app.core.document_processor.TextLoader')
    def test_load_document(self, mock_loader_class):
        """测试文档加载"""
        # 模拟文档加载器
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        
        # 模拟加载结果
        from langchain.schema import Document
        mock_docs = [Document(page_content="test content", metadata={"page": 1})]
        mock_loader.load.return_value = mock_docs
        
        # 测试加载
        result = self.processor.load_document("test.txt")
        
        assert len(result) == 1
        assert result[0].page_content == "test content"
        mock_loader_class.assert_called_once_with("test.txt")
        mock_loader.load.assert_called_once()
    
    def test_load_document_unsupported_format(self):
        """测试不支持的文件格式"""
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.processor.load_document("test.xyz")
    
    @patch('app.core.document_processor.RecursiveCharacterTextSplitter')
    def test_split_documents(self, mock_splitter_class):
        """测试文档分割"""
        from langchain.schema import Document
        
        # 模拟分割器
        mock_splitter = MagicMock()
        mock_splitter_class.return_value = mock_splitter
        
        # 模拟输入文档
        input_docs = [Document(page_content="long content", metadata={"source": "test.txt"})]
        
        # 模拟分割结果
        chunk1 = Document(page_content="chunk 1", metadata={"source": "test.txt"})
        chunk2 = Document(page_content="chunk 2", metadata={"source": "test.txt"})
        mock_splitter.split_documents.return_value = [chunk1, chunk2]
        
        # 测试分割
        result = self.processor.split_documents(input_docs)
        
        assert len(result) == 2
        assert result[0].page_content == "chunk 1"
        assert result[1].page_content == "chunk 2"
        
        # 验证每个块都有chunk_index和chunk_id
        assert 'chunk_index' in result[0].metadata
        assert 'chunk_index' in result[1].metadata
        assert 'chunk_id' in result[0].metadata
        assert 'chunk_id' in result[1].metadata
        
        mock_splitter.split_documents.assert_called_once_with(input_docs)
    
    @patch('app.core.document_processor.DocumentProcessor.load_document')
    @patch('app.core.document_processor.DocumentProcessor.split_documents')
    def test_process_document_success(self, mock_split, mock_load):
        """测试成功处理文档"""
        from langchain.schema import Document
        
        # 模拟加载结果
        loaded_docs = [Document(page_content="content", metadata={"page": 1})]
        mock_load.return_value = loaded_docs
        
        # 模拟分割结果
        chunks = [
            Document(page_content="chunk 1", metadata={"chunk_index": 0}),
            Document(page_content="chunk 2", metadata={"chunk_index": 1})
        ]
        mock_split.return_value = chunks
        
        # 测试处理
        result = self.processor.process_document("test.txt", "test.txt")
        
        assert result['status'] == 'completed'
        assert result['filename'] == 'test.txt'
        assert result['chunk_count'] == 2
        assert len(result['chunks']) == 2
        assert 'document_id' in result
        
        # 验证chunks中添加了文档元数据
        for chunk in result['chunks']:
            assert chunk.metadata['document_id'] == result['document_id']
            assert chunk.metadata['filename'] == 'test.txt'
    
    @patch('app.core.document_processor.DocumentProcessor.load_document')
    def test_process_document_failure(self, mock_load):
        """测试处理文档失败"""
        # 模拟加载失败
        mock_load.side_effect = Exception("Loading failed")
        
        # 测试处理
        result = self.processor.process_document("test.txt", "test.txt")
        
        assert result['status'] == 'failed'
        assert result['filename'] == 'test.txt'
        assert result['chunk_count'] == 0
        assert len(result['chunks']) == 0
        assert 'Loading failed' in result['error_message']