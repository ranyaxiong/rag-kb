# RAG知识库系统

一个基于RAG（Retrieval-Augmented Generation）技术的轻量级知识库应用，支持文档上传、智能问答和语义搜索。

## 🚀 特性

- **多格式文档支持**: PDF, Word, TXT, Markdown
- **智能问答**: 基于LangChain和OpenAI的RAG问答系统
- **语义搜索**: 使用ChromaDB进行向量相似度搜索
- **友好界面**: Streamlit构建的直观用户界面
- **容器化部署**: Docker和Docker Compose支持
- **CI/CD集成**: GitHub Actions自动化流程

## 🛠️ 技术栈

### 后端
- **FastAPI**: 高性能Web框架
- **LangChain**: LLM应用开发框架
- **ChromaDB**: 轻量级向量数据库
- **OpenAI**: GPT-3.5和Embedding服务

### 前端
- **Streamlit**: 快速构建数据应用界面
- **Python**: 统一的开发语言

### 部署
- **Docker**: 容器化部署
- **GitHub Actions**: CI/CD自动化

## 📦 安装部署

### 前置要求

- Python 3.11+
- Docker (可选)
- OpenAI API Key

### 本地开发

1. **克隆项目**
```bash
git clone <repository-url>
cd rag-kb-prototype
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API Key (安全方式)**

**推荐方式 - 系统环境变量:**
```bash
# Windows
set OPENAI_API_KEY=your-api-key-here

# Linux/Mac  
export OPENAI_API_KEY="your-api-key-here"
```

**替代方式 - 系统密钥环:**
```bash
pip install keyring
python scripts/setup-keyring.py
```

**开发环境 - 配置文件:**
```bash
cp .env.secure.example .env
# 按需配置OPENAI_API_KEY_FILE等选项
```

> 📖 详细安全配置请参考 [SECURITY.md](SECURITY.md)

5. **启动后端服务**
```bash
uvicorn app.main:app --reload
```

6. **启动前端服务（新终端）**
```bash
streamlit run frontend/streamlit_app.py
```

7. **访问应用**
- 后端API: http://localhost:8000
- 前端界面: http://localhost:8501
- API文档: http://localhost:8000/docs

### Docker部署

1. **配置环境变量**
```bash
cp .env.example .env
# 设置OPENAI_API_KEY
```

2. **启动服务**
```bash
cd docker
docker-compose up -d --build
```

3. **查看服务状态**
```bash
docker-compose ps
docker-compose logs -f
```

4. **访问应用**
- 前端界面: http://localhost:8501
- 后端API: http://localhost:8000

### 开发模式部署

```bash
cd docker
docker-compose -f docker-compose.dev.yml up -d --build
```

开发模式支持代码热重载。

## 📖 使用指南

### 1. 上传文档

在左侧边栏的"文档管理"区域：
- 选择支持的文件格式（PDF、Word、TXT、Markdown）
- 可以单个上传或批量上传
- 查看上传状态和处理进度

### 2. 智能问答

在主界面的"智能问答"区域：
- 输入自然语言问题
- 查看AI生成的答案
- 浏览相关的文档来源
- 对答案进行评分反馈

### 3. 文档管理

在右侧的"文档列表"区域：
- 查看已上传的文档
- 查看文档处理状态
- 删除不需要的文档

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api.py

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 测试覆盖率

测试覆盖率报告会生成在 `htmlcov/` 目录中。

## 🔧 配置选项

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | 必须设置 |
| `CHUNK_SIZE` | 文档分块大小 | 1000 |
| `CHUNK_OVERLAP` | 分块重叠大小 | 200 |
| `MAX_SOURCES` | 最大引用源数量 | 3 |
| `SIMILARITY_THRESHOLD` | 相似度阈值 | 0.7 |

### 支持的文件格式

- PDF (.pdf)
- Word文档 (.docx, .doc)
- 文本文件 (.txt)
- Markdown (.md)

## 🚀 部署到生产环境

### 1. 准备生产配置

```bash
# 创建生产环境配置
cp .env.example .env.prod

# 设置生产环境变量
# DEBUG=False
# OPENAI_API_KEY=your_production_key
```

### 2. 使用Docker部署

```bash
# 构建生产镜像
docker build -f docker/Dockerfile.backend -t rag-kb-backend:prod .
docker build -f docker/Dockerfile.frontend -t rag-kb-frontend:prod .

# 启动生产服务
docker-compose up -d
```

### 3. 健康检查

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查服务状态
docker-compose ps
```

## 🔍 监控和日志

### 应用日志

- 后端日志: 通过FastAPI的日志记录
- 前端日志: Streamlit自带的日志系统
- 容器日志: `docker-compose logs -f`

### 健康检查端点

- 后端健康检查: `GET /health`
- 问答系统健康检查: `GET /api/qa/health`
- 系统信息: `GET /info`

## 🤝 开发贡献

### 代码规范

项目使用以下代码规范工具：
- **Black**: 代码格式化
- **isort**: 导入排序
- **Flake8**: 代码检查

运行代码检查：
```bash
black app/ tests/
isort app/ tests/
flake8 app/ tests/
```

### 提交代码

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📋 待办事项

- [ ] 添加用户认证和权限管理
- [ ] 支持更多文档格式 (Excel, PowerPoint)
- [ ] 实现对话历史管理
- [ ] 添加文档预览功能
- [ ] 集成更多LLM模型选择
- [ ] 实现文档版本控制
- [ ] 添加搜索过滤和排序
- [ ] 性能优化和缓存机制

## ❓ 常见问题

### Q: 上传文档后无法问答？
A: 确保文档已经处理完成（状态显示为"completed"），并且设置了正确的OpenAI API Key。

### Q: Docker启动失败？
A: 检查端口是否被占用，确保.env文件配置正确，查看docker-compose logs获取详细错误信息。

### Q: 问答响应很慢？
A: 这可能是由于OpenAI API调用延迟，可以尝试调整max_sources参数或检查网络连接。

### Q: 如何增加支持的文件格式？
A: 在`app/core/document_processor.py`中的`loaders`字典中添加新的文件格式和对应的加载器。

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🆘 获取帮助

如果遇到问题或需要帮助：

1. 查看[常见问题](#-常见问题)
2. 提交[GitHub Issue](../../issues)
3. 查看项目文档和代码注释

## 🎯 路线图

### v1.0 (当前)
- ✅ 基础RAG问答功能
- ✅ 多格式文档支持
- ✅ Streamlit前端界面
- ✅ Docker容器化部署

### v1.1 (计划中)
- 🔲 用户认证系统
- 🔲 对话历史管理
- 🔲 文档标签和分类
- 🔲 搜索结果高亮

### v2.0 (未来)
- 🔲 多租户支持
- 🔲 API服务化
- 🔲 移动端支持
- 🔲 第三方集成

---

**享受使用RAG知识库系统！** 🚀