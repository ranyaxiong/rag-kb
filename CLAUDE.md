# RAG Knowledge Base - Claude Code Development Guide

This comprehensive guide provides everything a Claude Code instance needs to understand and work productively with the RAG Knowledge Base codebase.

## 🏗️ System Architecture

### Overview
A production-ready RAG (Retrieval-Augmented Generation) knowledge base application with FastAPI backend, Streamlit frontend, and multi-provider LLM support.

### Core Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Streamlit UI   │    │   FastAPI API   │    │  Document Proc  │
│  (Frontend)     │ ←→ │   (Backend)     │ ←→ │   (Core Logic)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ChromaDB      │    │   Vector Store  │    │   QA Engine     │
│   (Vector DB)   │ ←→ │   (Manager)     │ ←→ │   (RAG Logic)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 ↑
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Provider LLM Support                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   OpenAI     │ │   DeepSeek    │ │   Zhipu AI   │            │
│  │ GPT-3.5/4    │ │ deepseek-chat │ │   GLM-4      │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure
```
rag_kb/
├── app/                      # Backend application
│   ├── api/                  # API endpoints
│   │   ├── documents.py      # Document management API
│   │   └── qa.py            # Question-answering API
│   ├── core/                 # Core business logic
│   │   ├── config.py         # Multi-provider configuration
│   │   ├── document_processor.py # Document parsing & chunking
│   │   ├── qa_engine.py      # RAG question-answering engine
│   │   └── vector_store.py   # Vector database management
│   ├── models/
│   │   └── schemas.py        # Pydantic data models
│   └── main.py              # FastAPI application entry
├── frontend/                 # Streamlit frontend
│   ├── components/           # UI components
│   └── streamlit_app.py     # Main frontend app
├── docker/                   # Container configurations
│   ├── Dockerfile.backend    # Backend container
│   ├── Dockerfile.frontend   # Frontend container
│   ├── docker-compose.yml    # Production setup
│   └── docker-compose.dev.yml # Development setup
├── data/                     # Data storage
│   ├── uploads/             # Uploaded documents (date-organized)
│   └── chroma_db/           # ChromaDB vector storage
├── tests/                    # Test suite
├── scripts/                  # Automation scripts
└── secrets/                  # Secure credential storage
```

## 🚀 Quick Start Commands

### Development Setup
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# 2. Install dependencies
make install
# or: pip install -r requirements.txt

# 3. Configure API keys (see Multi-Provider Setup below)
make setup-keyring  # Recommended secure method
# or: cp .env.deepseek .env && edit API key

# 4. Start development mode (both backend + frontend)
make dev
# Backend: http://localhost:8000
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

### Docker Development
```bash
# Development mode with hot reload
make docker-dev
# or: cd docker && docker-compose -f docker-compose.dev.yml up -d

# Production mode
make docker-run
# or: cd docker && docker-compose up -d

# View logs
make docker-logs
# Stop services
make docker-stop
```

### Testing
```bash
# Run all tests with coverage
make test
# or: pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Generate HTML coverage report
make test-html
```

### Code Quality
```bash
# Format code
make format
# or: black app/ tests/ frontend/ && isort app/ tests/ frontend/

# Lint code
make lint
# or: flake8 app/ tests/ --max-line-length=88

# Clean cache files
make clean
```

## 🔧 Multi-Provider LLM Configuration

### Supported Providers
- **OpenAI**: GPT-3.5/4, text-embedding-ada-002
- **DeepSeek**: deepseek-chat, compatible with OpenAI embeddings
- **Zhipu AI (GLM)**: glm-4, embedding-2

### Quick Configuration
```bash
# DeepSeek (recommended - large free tier)
cp .env.deepseek .env
# Edit API_KEY=sk-your-deepseek-key-here

# Zhipu AI
cp .env.zhipu .env
# Edit API_KEY=your-zhipu-key-here

# OpenAI
export OPENAI_API_KEY="sk-your-openai-key-here"
```

### Secure Configuration (Recommended)
```bash
# Use system keyring (most secure)
make setup-keyring
# Follow prompts to store API key securely

# Verify configuration
make check-security
```

### Configuration Architecture
The `app/core/config.py` provides sophisticated multi-provider support:

```python
# Key configuration options
LLM_PROVIDER = "deepseek"  # or "openai", "zhipu"
EMBEDDING_PROVIDER = "openai"  # can differ from LLM provider
API_KEY = "your-api-key"  # or use secure methods
CHAT_MODEL = "deepseek-chat"  # auto-configured per provider
EMBEDDING_MODEL = "text-embedding-ada-002"
```

Multiple secure API key sources (in priority order):
1. Environment variables (`API_KEY`)
2. Secure files (`API_KEY_FILE`)
3. Base64 encoded (`API_KEY_BASE64`)
4. Docker secrets (`/run/secrets/`)
5. System keyring (Linux/Mac)
6. Backward compatibility with OpenAI-specific vars

## 🏠 Development Environment

### Local Development
```bash
# Terminal 1: Backend with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend with auto-reload
BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py

# Or use make command (runs both)
make dev
```

### Docker Development (Hot Reload)
```bash
# Start with source code mounting for hot reload
cd docker
docker-compose -f docker-compose.dev.yml up -d

# View real-time logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Health Checks
```bash
# Check all services
make health

# Manual checks
curl http://localhost:8000/health      # Backend health
curl http://localhost:8000/info        # System info
curl http://localhost:8501             # Frontend check
```

## 📄 Document Processing Pipeline

### Supported Formats
- **PDF**: PyPDFLoader
- **Word**: UnstructuredWordDocumentLoader (.docx, .doc)
- **Text**: TextLoader (.txt)
- **Markdown**: UnstructuredMarkdownLoader (.md)

### Processing Flow
1. **Upload** → File saved with UUID prefix in date-organized folders
2. **Parse** → Format-specific content extraction
3. **Chunk** → RecursiveCharacterTextSplitter (size: 1000, overlap: 200)
4. **Embed** → OpenAI/compatible embedding generation
5. **Store** → ChromaDB vector storage with metadata
6. **Index** → Available for RAG retrieval

### Key Classes
```python
# Document processing
from app.core.document_processor import DocumentProcessor
processor = DocumentProcessor()
result = processor.process_document(file_path, filename)

# Vector storage management
from app.core.vector_store import VectorStore
vector_store = VectorStore()  # Singleton pattern
doc_ids = vector_store.add_documents(chunks)

# RAG question answering
from app.core.qa_engine import QAEngine
qa_engine = QAEngine(vector_store)
response = qa_engine.ask(question)
```

## 🤖 RAG Question-Answering System

### QA Engine Architecture
- **Retriever**: ChromaDB similarity search (configurable k sources)
- **LLM**: Multi-provider chat models with custom prompts
- **Chain**: LangChain RetrievalQA with "stuff" strategy
- **Response**: Structured answer with source documents and timing

### Key Configuration
```python
# In app/core/config.py
MAX_SOURCES = 3              # Sources per query
SIMILARITY_THRESHOLD = 0.7   # Vector similarity threshold
CHUNK_SIZE = 1000           # Document chunk size
CHUNK_OVERLAP = 200         # Overlap between chunks
```

### Custom Prompt Template
The system uses a carefully crafted prompt template that:
- Encourages document-based answers
- Handles cases where information isn't available
- Requests structured, helpful responses
- Supports multi-point explanations

### Usage Examples
```python
# Basic question answering
response = qa_engine.ask("What is the main topic of the documents?")
print(response.answer)
print(f"Processing time: {response.processing_time}s")
for source in response.sources:
    print(f"Source: {source.document_name}")
    print(f"Content: {source.content}")

# Document retrieval only (no LLM generation)
docs = qa_engine.get_relevant_documents("search query", k=5)
```

## 🧪 Testing Framework

### Test Structure
```bash
tests/
├── conftest.py           # Pytest configuration and fixtures
├── test_api.py          # API endpoint tests
└── test_document_processor.py  # Core logic tests
```

### Key Testing Patterns
```python
# Mock settings for consistent testing
@pytest.fixture
def mock_settings():
    with patch('app.core.config.settings') as mock:
        mock.openai_api_key = "test-key"
        mock.upload_dir = "/tmp/test_uploads"
        # ... other test configurations
        yield mock

# API testing with FastAPI TestClient
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
```

### Coverage Requirements
- Minimum coverage: 70% (configured in pytest.ini)
- HTML reports generated in `htmlcov/`
- Focus on core business logic and API endpoints

## 🐳 Docker & Deployment

### Container Architecture
- **Backend**: Python 3.11 slim with FastAPI + dependencies
- **Frontend**: Streamlit with backend connectivity
- **Development**: Volume mounts for hot reload
- **Production**: Optimized images with health checks

### Environment Configurations

**Development** (docker-compose.dev.yml):
- Source code volume mounting
- Hot reload enabled
- Debug logging
- Simplified networking

**Production** (docker-compose.yml):
- Optimized images
- Health checks enabled
- Restart policies
- Environment variable management

### Deployment Commands
```bash
# Development deployment
make docker-dev

# Production deployment
make docker-run

# Check service status
make docker-ps

# View logs
make docker-logs

# Scale services (if needed)
docker-compose up -d --scale backend=2
```

## 🔐 Security Best Practices

### API Key Management
The system implements multiple secure API key storage methods:

1. **System Environment Variables** (Recommended)
2. **System Keyring** (Most Secure)
3. **Docker Secrets** (Production)
4. **Encrypted Files** (Limited use)

### Security Checklist
- ✅ Never commit API keys to Git
- ✅ Use `.gitignore` for sensitive files
- ✅ Implement secure key rotation
- ✅ Monitor API usage and costs
- ✅ Use HTTPS in production
- ✅ Enable CORS appropriately
- ✅ Validate file uploads (size, type)

### Emergency Procedures
If API keys are compromised:
1. Immediately revoke compromised keys
2. Generate new keys
3. Update all services using secure methods
4. Review logs for unauthorized usage
5. Document incident and improve procedures

## 📊 Monitoring & Debugging

### Health Check Endpoints
```bash
# Backend system health
GET /health
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0"
}

# QA system health
GET /api/qa/health
{
  "success": true,
  "health": {
    "status": "healthy",
    "llm": "connected",
    "vector_store": "healthy",
    "qa_chain": "working"
  }
}

# System information
GET /info
```

### Logging Strategy
- **Structured Logging**: JSON format for production
- **Log Levels**: INFO for normal operations, DEBUG for development
- **Log Files**: Stored in `logs/` directory
- **Rotation**: Automatic log rotation in production

### Common Issues & Solutions

**Issue**: API key not found
```bash
# Check configuration
python -c "from app.core.config import settings; print(bool(settings.get_api_key()))"

# Verify environment
make check-security
```

**Issue**: Document processing fails
```bash
# Check supported formats
curl http://localhost:8000/api/documents/stats/overview

# Verify file permissions
ls -la data/uploads/
```

**Issue**: Vector search returns no results
```bash
# Check collection info
curl http://localhost:8000/api/qa/stats

# Verify documents are indexed
curl http://localhost:8000/api/documents/
```

## 🔄 CI/CD Pipeline

### GitHub Actions Integration
The repository includes CI/CD workflows for:
- **Testing**: Automated test execution on PR/push
- **Linting**: Code quality checks
- **Docker**: Container image building
- **Deployment**: Production deployment automation

### Local CI Testing
```bash
# Run full build process
make build

# This executes:
# 1. Clean cache and temp files
# 2. Install fresh dependencies
# 3. Run complete test suite
# 4. Verify all tests pass
```

## 🎯 Common Development Tasks

### Adding New Document Formats
1. Extend `loaders` dict in `DocumentProcessor`
2. Add format-specific dependencies to `requirements.txt`
3. Update tests and documentation

### Implementing New LLM Providers
1. Add provider configuration to `Settings.get_model_config()`
2. Update provider-specific API endpoints
3. Test compatibility with existing RAG pipeline

### Frontend Customization
1. Modify Streamlit components in `frontend/components/`
2. Update main interface in `streamlit_app.py`
3. Test responsive behavior and error handling

### Performance Optimization
1. Adjust chunk sizes in configuration
2. Implement caching for frequent queries
3. Optimize vector search parameters
4. Monitor LLM token usage

## 📋 Development Checklist

When working on this codebase:

### Before Starting
- [ ] Verify API keys are configured securely
- [ ] Confirm backend and frontend services start successfully
- [ ] Run health checks to ensure system readiness
- [ ] Review recent commits for context

### During Development
- [ ] Use appropriate testing with `make test`
- [ ] Follow code formatting with `make format`
- [ ] Check linting with `make lint`
- [ ] Test both local and Docker environments

### Before Committing
- [ ] Ensure all tests pass
- [ ] Verify code formatting is consistent
- [ ] Check that no secrets are being committed
- [ ] Update documentation if needed
- [ ] Test end-to-end functionality

### Production Deployment
- [ ] Use production Docker configuration
- [ ] Enable proper monitoring and logging
- [ ] Verify security configurations
- [ ] Test with representative data load
- [ ] Plan rollback procedures

## 🤝 Architecture Principles

This codebase follows several key architectural principles:

### Separation of Concerns
- **API Layer**: Clean REST endpoints with proper validation
- **Business Logic**: Core RAG functionality isolated in `core/` modules
- **Data Layer**: Abstracted database interactions
- **Presentation**: Streamlit UI components separate from logic

### Configuration Management
- **Environment-based**: Different configs for dev/prod
- **Secure by Default**: Multiple secure API key storage options
- **Provider-agnostic**: Easy switching between LLM providers

### Scalability Considerations
- **Singleton Pattern**: Efficient resource management for vector store
- **Async Processing**: Background document processing
- **Containerization**: Easy horizontal scaling with Docker
- **Stateless Design**: Services can be replicated as needed

### Error Handling
- **Graceful Degradation**: System continues operating with partial failures
- **Informative Messages**: User-friendly error communication
- **Comprehensive Logging**: Detailed error tracking for debugging

## 🛡️ Development Best Practices

These practices help avoid incomplete integrations and ensure robust feature implementation:

### 1. 立即验证原则 (Immediate Verification Principle)
Never assume code changes work without immediate testing:

```python
# ❌ Wrong approach
def implement_feature():
    create_new_class()
    modify_config()
    # Test later...

# ✅ Correct approach  
def implement_feature():
    create_new_class()
    test_class_works()      # Verify immediately
    modify_config() 
    test_integration()      # Verify immediately
```

**Key Rules:**
- Test each component immediately after creation
- Verify configuration changes take effect
- Don't batch all testing to the end

### 2. 端到端测试驱动 (End-to-End Test-Driven Development)
Always validate the complete workflow:

```python
# Create comprehensive integration tests
def test_complete_workflow():
    # Test: Upload → Process → Store → Retrieve → Query
    # Verify each step works in the full chain
```

**Implementation:**
- Create "smoke tests" for quick validation
- Run full workflow tests after any integration changes
- Don't trust "it should work" - prove it with tests
- Test both success and failure scenarios

### 3. 增量集成策略 (Incremental Integration Strategy)
Build and integrate features step by step:

```
Step 1: Create new component + Unit tests ✅
Step 2: Integrate to system + Integration tests ✅  
Step 3: Verify existing functionality unchanged ✅
Step 4: Verify new functionality works as expected ✅
```

**Guidelines:**
- Never integrate multiple changes simultaneously
- Validate each integration point separately
- Maintain rollback capability at each step
- Document integration dependencies

### 4. 建立验证检查清单 (Establish Verification Checklists)
Use systematic checklists for feature integration:

**New Feature Integration Checklist:**
- [ ] New classes instantiate correctly?
- [ ] Configuration updated and effective?
- [ ] Call chain routing correct?
- [ ] End-to-end workflow functional?
- [ ] Existing features unaffected?
- [ ] Error handling working?
- [ ] Performance acceptable?
- [ ] Documentation updated?

**PDF Processing Specific Checklist:**
- [ ] Document processor uses new loader class?
- [ ] Enhanced processor handles both text and scanned PDFs?
- [ ] Fallback mechanisms work correctly?
- [ ] OCR dependencies available and functional?
- [ ] Error messages provide helpful guidance?

### 5. 使用追踪和日志 (Use Tracing and Logging)
Add strategic logging to verify execution paths:

```python
import logging
logger = logging.getLogger(__name__)

def load_document(self, file_path):
    loader_class = self.loaders['.pdf']
    logger.info(f"Using PDF loader: {loader_class.__name__}")
    
    loader = loader_class(file_path)
    logger.info(f"Loader initialized: {type(loader)}")
    
    documents = loader.load()
    logger.info(f"Loaded {len(documents)} documents successfully")
    
    return documents
```

**Logging Strategy:**
- Log critical decision points and class selections
- Include timing information for performance monitoring
- Log both successful operations and fallback activations
- Use structured logging for easier analysis
- Different log levels for development vs production

**Verification Commands:**
```bash
# Quick integration verification
python -c "
from app.core.document_processor import DocumentProcessor
proc = DocumentProcessor()
print(f'PDF Loader: {proc.loaders[\".pdf\"].__name__}')
"

# Test class instantiation  
python -c "
from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
proc = EnhancedPDFProcessor()
print(f'OCR Available: {proc.ocr_available}')
"
```

### Integration Testing Commands
```bash
# Run integration verification
python test_end_to_end.py

# Test specific component
python -m pytest tests/test_pdf_processing.py -v

# Verify API integration
curl http://localhost:8000/api/documents/stats/overview
```

This guide should provide everything needed for a Claude Code instance to quickly understand and productively work with this RAG knowledge base codebase. The system is well-architected with clear separation of concerns, comprehensive configuration options, and robust development practices that ensure reliable feature integration.