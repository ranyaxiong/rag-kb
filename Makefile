# Makefile for RAG Knowledge Base

.PHONY: help install test lint format clean build run stop docker-build docker-run docker-stop

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)RAG Knowledge Base - 可用命令:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## 安装项目依赖
	@echo "$(YELLOW)📦 安装项目依赖...$(NC)"
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	mkdir -p data/uploads data/chroma_db logs

test: ## 运行测试
	@echo "$(YELLOW)🧪 运行测试...$(NC)"
	pytest tests/ -v --cov=app --cov-report=term-missing

test-html: ## 运行测试并生成HTML覆盖率报告
	@echo "$(YELLOW)🧪 运行测试并生成HTML报告...$(NC)"
	pytest tests/ -v --cov=app --cov-report=html
	@echo "$(GREEN)📊 覆盖率报告生成在 htmlcov/index.html$(NC)"

lint: ## 代码检查
	@echo "$(YELLOW)🔍 运行代码检查...$(NC)"
	flake8 app/ tests/ --max-line-length=88 --extend-ignore=E203,W503

format: ## 格式化代码
	@echo "$(YELLOW)✨ 格式化代码...$(NC)"
	black app/ tests/ frontend/
	isort app/ tests/ frontend/

clean: ## 清理缓存和临时文件
	@echo "$(YELLOW)🧹 清理缓存文件...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

env: ## 创建环境配置文件
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)📝 创建安全的环境配置文件...$(NC)"; \
		cp .env.secure.example .env; \
		echo "$(GREEN)✅ .env文件已创建$(NC)"; \
		echo "$(BLUE)🔐 请选择安全的API Key配置方式:$(NC)"; \
		echo "   1. 系统环境变量: export OPENAI_API_KEY='your-key'"; \
		echo "   2. 系统密钥环: python scripts/setup-keyring.py"; \
		echo "   3. 密钥文件: ./scripts/setup-secrets.sh"; \
		echo "   4. 详细指南: cat SECURITY.md"; \
	else \
		echo "$(BLUE)ℹ️  .env文件已存在$(NC)"; \
	fi

setup-keyring: ## 设置系统密钥环存储API Key
	@echo "$(YELLOW)🔐 设置系统密钥环...$(NC)"
	python scripts/setup-keyring.py

setup-secrets: ## 设置Docker secrets
	@echo "$(YELLOW)🔐 设置Docker secrets...$(NC)"
	./scripts/setup-secrets.sh

check-security: ## 检查安全配置
	@echo "$(YELLOW)🔍 检查安全配置...$(NC)"
	@python -c "from app.core.config import settings; key=settings.get_openai_api_key(); print('✅ API Key已配置' if key else '❌ API Key未配置')"

dev: ## 启动本地开发模式
	@echo "$(YELLOW)🔧 启动本地开发模式...$(NC)"
	@make env
	@echo "$(YELLOW)🚀 启动后端服务...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "$(YELLOW)⏳ 等待后端启动...$(NC)"
	@sleep 5
	@echo "$(YELLOW)🎨 启动前端服务...$(NC)"
	BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py --server.port 8501

run: ## 启动生产模式
	@echo "$(YELLOW)🚀 启动生产模式...$(NC)"
	@make env
	uvicorn app.main:app --host 0.0.0.0 --port 8000 &
	@sleep 5
	BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py --server.port 8501

stop: ## 停止本地服务
	@echo "$(YELLOW)🛑 停止服务...$(NC)"
	@pkill -f "uvicorn app.main:app" || true
	@pkill -f "streamlit run frontend/streamlit_app.py" || true
	@if [ -f backend.pid ]; then \
		kill $(cat backend.pid) 2>/dev/null || true; \
		rm backend.pid; \
	fi
	@echo "$(GREEN)✅ 服务已停止$(NC)"

# Docker相关命令
docker-build: ## 构建Docker镜像
	@echo "$(YELLOW)🐳 构建Docker镜像...$(NC)"
	cd docker && docker-compose build

docker-run: ## 启动Docker服务
	@echo "$(YELLOW)🐳 启动Docker服务...$(NC)"
	@make env
	cd docker && docker-compose up -d
	@echo "$(GREEN)✅ Docker服务启动完成$(NC)"
	@echo "$(BLUE)🌐 前端地址: http://localhost:8501$(NC)"
	@echo "$(BLUE)🔗 后端API: http://localhost:8000$(NC)"

docker-dev: ## 启动Docker开发模式
	@echo "$(YELLOW)🐳 启动Docker开发模式...$(NC)"
	@make env
	cd docker && docker-compose -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✅ Docker开发模式启动完成$(NC)"

docker-stop: ## 停止Docker服务
	@echo "$(YELLOW)🐳 停止Docker服务...$(NC)"
	cd docker && docker-compose down
	cd docker && docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	@echo "$(GREEN)✅ Docker服务已停止$(NC)"

docker-logs: ## 查看Docker日志
	cd docker && docker-compose logs -f

docker-ps: ## 查看Docker服务状态
	cd docker && docker-compose ps

# 部署相关
build: ## 构建应用
	@echo "$(YELLOW)🔨 构建应用...$(NC)"
	@make clean
	@make install
	@make test

deploy-dev: ## 部署到开发环境
	@echo "$(YELLOW)🚀 部署到开发环境...$(NC)"
	@make docker-build
	@make docker-run

deploy-prod: ## 部署到生产环境
	@echo "$(YELLOW)🚀 部署到生产环境...$(NC)"
	@echo "$(RED)⚠️  请确保已经设置了生产环境配置$(NC)"
	@make docker-build
	# 这里添加生产部署命令

# 工具命令
check-env: ## 检查环境配置
	@echo "$(YELLOW)🔍 检查环境配置...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env文件不存在$(NC)"; \
		exit 1; \
	fi
	@if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then \
		echo "$(RED)❌ OpenAI API Key未配置$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ 环境配置检查通过$(NC)"

health: ## 检查服务健康状态
	@echo "$(YELLOW)🔍 检查服务健康状态...$(NC)"
	@curl -s http://localhost:8000/health || echo "$(RED)❌ 后端服务未响应$(NC)"
	@curl -s http://localhost:8501 > /dev/null || echo "$(RED)❌ 前端服务未响应$(NC)"

logs: ## 查看应用日志
	@if [ -f logs/backend.log ]; then \
		echo "$(YELLOW)📋 后端日志:$(NC)"; \
		tail -f logs/backend.log; \
	else \
		echo "$(RED)❌ 未找到后端日志文件$(NC)"; \
	fi

# 开发工具
setup-dev: ## 设置开发环境
	@echo "$(YELLOW)🔧 设置开发环境...$(NC)"
	python -m venv venv
	@echo "$(GREEN)✅ 虚拟环境创建完成$(NC)"
	@echo "$(BLUE)📝 请运行以下命令激活虚拟环境:$(NC)"
	@echo "   source venv/bin/activate  # Linux/Mac"
	@echo "   venv\\Scripts\\activate     # Windows"
	@echo "$(BLUE)然后运行: make install$(NC)"

info: ## 显示项目信息
	@echo "$(BLUE)📋 项目信息:$(NC)"
	@echo "  名称: RAG Knowledge Base"
	@echo "  版本: 1.0.0"
	@echo "  Python: $(shell python --version 2>/dev/null || echo 'Not installed')"
	@echo "  Docker: $(shell docker --version 2>/dev/null | cut -d' ' -f3 | cut -d',' -f1 || echo 'Not installed')"
	@echo "  工作目录: $(PWD)"