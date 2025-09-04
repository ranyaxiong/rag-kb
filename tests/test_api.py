"""
API接口测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app

client = TestClient(app)


class TestHealthAPI:
    """健康检查API测试"""
    
    def test_root_endpoint(self):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "timestamp" in data
    
    @patch('app.main.settings')
    @patch('os.path.exists')
    def test_health_check_healthy(self, mock_exists, mock_settings):
        """测试健康检查 - 正常状态"""
        # 模拟配置
        mock_settings.openai_api_key = "test-key"
        mock_settings.app_version = "1.0.0"
        mock_exists.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
    
    @patch('app.main.settings')
    @patch('os.path.exists')
    def test_health_check_degraded(self, mock_exists, mock_settings):
        """测试健康检查 - 降级状态"""
        # 模拟部分配置缺失
        mock_settings.openai_api_key = None
        mock_settings.app_version = "1.0.0"
        mock_exists.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
    
    def test_info_endpoint(self):
        """测试系统信息端点"""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "chunk_size" in data


class TestDocumentAPI:
    """文档管理API测试"""
    
    @patch('app.api.documents.doc_processor')
    def test_upload_document_success(self, mock_processor):
        """测试成功上传文档"""
        # 模拟处理器
        mock_processor.is_supported_file.return_value = True
        mock_processor.save_uploaded_file.return_value = "/path/to/file.txt"
        mock_processor.get_document_info.return_value = {
            'file_type': '.txt',
            'file_size': 1024,
        }
        
        # 模拟文件上传
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = client.post("/api/documents/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "document" in data
    
    @patch('app.api.documents.doc_processor')
    def test_upload_unsupported_file(self, mock_processor):
        """测试上传不支持的文件格式"""
        mock_processor.is_supported_file.return_value = False
        
        files = {"file": ("test.xyz", b"test content", "application/xyz")}
        response = client.post("/api/documents/upload", files=files)
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_upload_large_file(self):
        """测试上传超大文件"""
        # 创建超过10MB的文件内容
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        files = {"file": ("large.txt", large_content, "text/plain")}
        response = client.post("/api/documents/upload", files=files)
        
        assert response.status_code == 400
        assert "File size too large" in response.json()["detail"]
    
    @patch('app.api.documents.vector_store')
    def test_list_documents(self, mock_vector_store):
        """测试获取文档列表"""
        # 模拟向量存储返回的文档列表
        mock_vector_store.list_documents.return_value = [
            {
                'document_id': 'doc1',
                'filename': 'test1.txt',
                'chunk_count': 5,
                'processed_at': '2023-01-01T00:00:00'
            }
        ]
        
        response = client.get("/api/documents/")
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) == 1
        assert documents[0]['filename'] == 'test1.txt'
    
    @patch('app.api.documents.vector_store')
    def test_get_document_found(self, mock_vector_store):
        """测试获取文档详情 - 找到文档"""
        mock_vector_store.list_documents.return_value = [
            {
                'document_id': 'doc1',
                'filename': 'test1.txt',
                'chunk_count': 5
            }
        ]
        
        response = client.get("/api/documents/doc1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document"]["filename"] == "test1.txt"
    
    @patch('app.api.documents.vector_store')
    def test_get_document_not_found(self, mock_vector_store):
        """测试获取文档详情 - 文档不存在"""
        mock_vector_store.list_documents.return_value = []
        
        response = client.get("/api/documents/nonexistent")
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]
    
    @patch('app.api.documents.vector_store')
    def test_delete_document_success(self, mock_vector_store):
        """测试成功删除文档"""
        mock_vector_store.delete_document_by_id.return_value = True
        
        response = client.delete("/api/documents/doc1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('app.api.documents.vector_store')
    def test_delete_document_not_found(self, mock_vector_store):
        """测试删除不存在的文档"""
        mock_vector_store.delete_document_by_id.return_value = False
        
        response = client.delete("/api/documents/nonexistent")
        assert response.status_code == 404


class TestQAAPI:
    """问答API测试"""
    
    @patch('app.api.qa.vector_store')
    @patch('app.api.qa.qa_engine')
    def test_ask_question_success(self, mock_qa_engine, mock_vector_store):
        """测试成功回答问题"""
        # 模拟有文档数据
        mock_vector_store.get_collection_info.return_value = {"document_count": 5}
        
        # 模拟问答引擎响应
        from app.models.schemas import QuestionResponse, SourceDocument
        mock_response = QuestionResponse(
            answer="这是测试答案",
            sources=[
                SourceDocument(
                    document_name="test.txt",
                    content="相关内容",
                    similarity_score=0.9
                )
            ],
            processing_time=1.5
        )
        mock_qa_engine.ask.return_value = mock_response
        
        # 发送请求
        request_data = {"question": "测试问题", "max_sources": 3}
        response = client.post("/api/qa/ask", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "这是测试答案"
        assert len(data["sources"]) == 1
        assert data["processing_time"] == 1.5
    
    @patch('app.api.qa.vector_store')
    def test_ask_question_no_documents(self, mock_vector_store):
        """测试没有文档时的问答"""
        # 模拟没有文档数据
        mock_vector_store.get_collection_info.return_value = {"document_count": 0}
        
        request_data = {"question": "测试问题"}
        response = client.post("/api/qa/ask", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "知识库中暂时没有文档" in data["answer"]
        assert len(data["sources"]) == 0
    
    def test_ask_empty_question(self):
        """测试空问题"""
        request_data = {"question": "  "}
        response = client.post("/api/qa/ask", json=request_data)
        
        assert response.status_code == 400
        assert "Question cannot be empty" in response.json()["detail"]
    
    @patch('app.api.qa.qa_engine')
    def test_search_documents(self, mock_qa_engine):
        """测试文档检索"""
        from langchain_core.documents import Document
        
        # 模拟检索结果
        mock_docs = [
            Document(
                page_content="相关内容1",
                metadata={"filename": "test1.txt", "document_id": "doc1", "chunk_index": 0}
            ),
            Document(
                page_content="相关内容2",
                metadata={"filename": "test2.txt", "document_id": "doc2", "chunk_index": 1}
            )
        ]
        mock_qa_engine.get_relevant_documents.return_value = mock_docs
        
        request_data = {"question": "测试查询", "max_sources": 5}
        response = client.post("/api/qa/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 2
        assert data["total_found"] == 2
    
    @patch('app.api.qa.vector_store')
    def test_get_suggestions_no_documents(self, mock_vector_store):
        """测试获取问题建议 - 无文档"""
        mock_vector_store.get_collection_info.return_value = {"document_count": 0}
        
        response = client.get("/api/qa/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert "请先上传一些文档" in data["suggestions"]
    
    @patch('app.api.qa.vector_store')
    def test_get_suggestions_with_documents(self, mock_vector_store):
        """测试获取问题建议 - 有文档"""
        mock_vector_store.get_collection_info.return_value = {"document_count": 5}
        
        response = client.get("/api/qa/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) > 0
        assert data["document_count"] == 5
    
    def test_submit_feedback_valid(self):
        """测试提交有效反馈"""
        feedback_data = {
            "question": "测试问题",
            "answer": "测试答案",
            "rating": 4,
            "feedback": "很好的答案"
        }
        
        response = client.post("/api/qa/feedback", json=feedback_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_submit_feedback_invalid_rating(self):
        """测试提交无效评分"""
        feedback_data = {
            "question": "测试问题",
            "answer": "测试答案",
            "rating": 6  # 无效评分
        }
        
        response = client.post("/api/qa/feedback", json=feedback_data)
        assert response.status_code == 400
        assert "Rating must be between 1 and 5" in response.json()["detail"]


class TestAPIIntegration:
    """集成测试"""
    
    @patch('app.api.documents.doc_processor')
    @patch('app.api.documents.vector_store')
    @patch('app.api.qa.qa_engine')
    def test_full_workflow(self, mock_qa_engine, mock_vector_store, mock_processor):
        """测试完整工作流程：上传文档 -> 问答"""
        # 1. 模拟文档上传
        mock_processor.is_supported_file.return_value = True
        mock_processor.save_uploaded_file.return_value = "/path/to/file.txt"
        mock_processor.get_document_info.return_value = {
            'file_type': '.txt',
            'file_size': 1024,
        }
        
        files = {"file": ("test.txt", b"test content", "text/plain")}
        upload_response = client.post("/api/documents/upload", files=files)
        assert upload_response.status_code == 200
        
        # 2. 模拟问答
        mock_vector_store.get_collection_info.return_value = {"document_count": 1}
        
        from app.models.schemas import QuestionResponse, SourceDocument
        mock_response = QuestionResponse(
            answer="基于文档的答案",
            sources=[
                SourceDocument(
                    document_name="test.txt",
                    content="相关内容",
                    similarity_score=0.8
                )
            ],
            processing_time=1.0
        )
        mock_qa_engine.ask.return_value = mock_response
        
        qa_request = {"question": "关于文档的问题"}
        qa_response = client.post("/api/qa/ask", json=qa_request)
        assert qa_response.status_code == 200
        
        qa_data = qa_response.json()
        assert "基于文档的答案" in qa_data["answer"]
        assert len(qa_data["sources"]) > 0