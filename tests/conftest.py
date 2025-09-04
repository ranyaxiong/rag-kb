"""
pytest配置文件
"""
import pytest
import tempfile
import os
from unittest.mock import patch

@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def mock_settings():
    """模拟设置fixture"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.upload_dir = "/tmp/test_uploads"
        mock_settings.chroma_db_path = "/tmp/test_chroma"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_settings.max_sources = 3
        mock_settings.similarity_threshold = 0.7
        mock_settings.app_name = "RAG Knowledge Base"
        mock_settings.app_version = "1.0.0"
        mock_settings.debug = False
        yield mock_settings

@pytest.fixture
def sample_document():
    """示例文档fixture"""
    return {
        "content": "This is a test document content for RAG testing.",
        "metadata": {
            "filename": "test.txt",
            "document_id": "test-doc-123",
            "page": 1
        }
    }

@pytest.fixture(autouse=True)
def mock_openai_key():
    """自动模拟OpenAI API Key"""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        yield

@pytest.fixture
def mock_vector_store():
    """模拟向量存储fixture"""
    with patch('app.core.vector_store.VectorStore') as mock_vs:
        mock_instance = mock_vs.return_value
        mock_instance.get_collection_info.return_value = {"document_count": 0}
        mock_instance.list_documents.return_value = []
        mock_instance.add_documents.return_value = True
        mock_instance.delete_document_by_id.return_value = True
        yield mock_instance

@pytest.fixture
def test_document_content():
    """测试文档内容fixture"""
    return "This is a test document with some content for testing purposes. " * 10