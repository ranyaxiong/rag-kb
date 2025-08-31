#!/bin/bash
# 停止脚本

set -e

echo "🛑 停止RAG知识库系统..."

# 检查是否有Docker服务运行
if [ -f "docker/docker-compose.yml" ] && docker-compose -f docker/docker-compose.yml ps -q | grep -q .; then
    echo "🐳 停止Docker服务..."
    cd docker
    docker-compose down
    echo "✅ Docker服务已停止"
fi

# 检查是否有开发模式Docker服务运行
if [ -f "docker/docker-compose.dev.yml" ] && docker-compose -f docker/docker-compose.dev.yml ps -q | grep -q .; then
    echo "🐳 停止Docker开发模式服务..."
    cd docker
    docker-compose -f docker-compose.dev.yml down
    echo "✅ Docker开发模式服务已停止"
fi

# 停止本地后端服务
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "🔧 停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm backend.pid
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  后端服务PID文件存在但进程不存在，清理PID文件"
        rm backend.pid
    fi
fi

# 清理可能的残留进程
echo "🧹 清理残留进程..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "streamlit run frontend/streamlit_app.py" 2>/dev/null || true

echo "✅ RAG知识库系统已完全停止"