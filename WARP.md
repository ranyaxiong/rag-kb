# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Core Architecture

This is a production-ready RAG (Retrieval-Augmented Generation) knowledge base application with:

- **Backend**: FastAPI with multi-provider LLM support (OpenAI, DeepSeek, Zhipu AI)
- **Frontend**: Streamlit web interface with real-time chat
- **Vector Store**: ChromaDB for document embeddings and similarity search
- **Document Processing**: Support for PDF, Word, TXT, Markdown with async processing
- **Deployment**: Docker containerization with development and production modes

### Key Components Flow
```
Documents → DocumentProcessor → Vector Store (ChromaDB) → QA Engine → LLM → Response
```

## Development Commands

### Local Development Setup
```bash
# Setup virtual environment and dependencies
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure API keys (multiple options available)
export API_KEY="your-api-key"  # Generic key
export OPENAI_API_KEY="sk-..."  # OpenAI specific
# or use .env file, keyring, Docker secrets

# Start backend (terminal 1)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (terminal 2) 
BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py
```

### Docker Development
```bash
# Development mode (with hot reload)
cd docker
docker-compose -f docker-compose.dev.yml up -d --build

# Production mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Testing
```bash
# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Test document processing
python test_end_to_end.py

# Test PDF processing specifically
python test_pdf_processing.py
```

### Code Quality
```bash
# Format code
black app/ tests/ frontend/
isort app/ tests/ frontend/

# Lint code
flake8 app/ tests/ --max-line-length=88
```

## Architecture Deep Dive

### Multi-Provider LLM Support
The system supports multiple LLM providers through unified configuration:

- **OpenAI**: GPT-3.5/4, text-embedding-ada-002
- **DeepSeek**: deepseek-chat (cost-effective option)  
- **Zhipu AI**: GLM-4, embedding-2

Configuration is handled in `app/core/config.py` with automatic provider-specific defaults and fallbacks.

### Document Processing Pipeline
1. **Upload**: Files saved with UUID prefix in date-organized folders (`data/uploads/YYYY-MM-DD/`)
2. **Processing**: Format-specific loaders (PDF, Word, TXT, Markdown)
3. **Chunking**: RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
4. **Embedding**: Provider-specific embedding generation
5. **Storage**: ChromaDB vector storage with metadata
6. **Indexing**: Available for similarity search and RAG

### RAG Question-Answering System
- **Retrieval**: ChromaDB similarity search with configurable sources (default: 3)
- **Context Building**: Retrieved chunks formatted as context
- **Generation**: LLM generates answer with source attribution
- **Fallback Logic**: Handles document-specific vs global search with automatic fallback

### Key Configuration Options
```python
# Core RAG settings (app/core/config.py)
CHUNK_SIZE = 1000              # Document chunk size
CHUNK_OVERLAP = 200            # Overlap between chunks  
MAX_SOURCES = 3                # Sources per query
SIMILARITY_THRESHOLD = 1.5     # ChromaDB distance threshold
RELEVANCE_FALLBACK_THRESHOLD = 0.5  # Strict relevance threshold
```

### API Structure
- **Documents API** (`/api/documents/`): Upload, list, delete, stats
- **QA API** (`/api/qa/`): Ask questions, health checks, quota management
- **Cost Optimization** (`/api/cost/`): Cache management, usage tracking

### Async Processing
The system supports both synchronous and asynchronous document processing:
- Synchronous: Immediate processing with response
- Asynchronous: Background processing with job status tracking
- Thread pool execution for scalable background processing

### Security Features
- Multiple secure API key storage methods (environment, keyring, Docker secrets, files)
- CORS configuration for frontend access
- File upload validation (type, size limits)
- Request quota management for demo/public usage

## Common Development Tasks

### Adding New Document Format Support
1. Extend `loaders` dictionary in `app/core/document_processor.py`
2. Add format-specific dependencies to `requirements.txt`
3. Update `supported_extensions` set
4. Test with representative files

### Implementing New LLM Provider
1. Add provider configuration to `Settings.get_model_config()` in `config.py`
2. Set provider-specific defaults (API base URL, model names)
3. Test compatibility with existing RAG pipeline
4. Update documentation and examples

### Frontend Customization
1. Modify Streamlit components in `frontend/components/`
2. Update main interface in `frontend/streamlit_app.py`
3. Test responsive behavior and BYOK (Bring Your Own Key) functionality

### Testing Strategy
- **Unit Tests**: Core business logic in `app/core/`
- **Integration Tests**: API endpoints with TestClient
- **End-to-End Tests**: Complete document upload → processing → QA workflow
- **Mock Strategy**: Test environment uses mocked LLM responses for stability

## Troubleshooting

### Common Issues
- **API Key Configuration**: Use `python -c "from app.core.config import settings; print(bool(settings.get_api_key()))"` to verify
- **Document Processing**: Check `data/uploads/` permissions and supported file formats
- **Vector Search**: Verify documents are indexed with `/api/documents/stats/overview`
- **Backend Connection**: Frontend shows connection status and backend URL configuration

### Health Check Endpoints
- Backend: `GET /health`
- QA System: `GET /api/qa/health` 
- System Info: `GET /info`

### Service URLs (Default)
- Frontend UI: http://localhost:8501
- Backend API: http://localhost:8000  
- API Documentation: http://localhost:8000/docs

## Development Best Practices

### Error Handling
The codebase follows graceful degradation principles:
- Demo mode when no API key is provided (shows retrieval results only)
- Automatic fallback between document-specific and global search
- Comprehensive error messages for user guidance
- Structured logging for debugging

### Performance Considerations
- Singleton pattern for vector store to avoid reinitialization
- Configurable batch processing for embeddings
- Caching mechanisms for repeated queries
- Async processing for large document uploads

### Security Guidelines
- Never commit API keys to Git
- Use secure key storage methods (keyring, Docker secrets, environment variables)
- Validate all file uploads (size, type, content)
- Implement proper CORS policies for production deployment

## Project Structure Notes

The codebase uses clear separation of concerns:
- `app/api/`: REST API endpoints with FastAPI
- `app/core/`: Business logic (document processing, QA engine, vector store)
- `app/models/`: Pydantic schemas for request/response validation
- `frontend/`: Streamlit UI with modular components
- `docker/`: Container configurations for different environments
- `tests/`: Comprehensive test suite with fixtures and mocks

The architecture is designed for scalability with stateless services, containerization, and configurable resource limits.
