#!/bin/bash
# 启动脚本

set -e

echo "🚀 启动RAG知识库系统..."

# 检查环境文件
if [ ! -f .env ]; then
    echo "⚠️  .env文件不存在，正在从示例创建..."
    cp .env.example .env
    echo "📝 请编辑.env文件设置你的OpenAI API Key"
    echo "然后重新运行此脚本"
    exit 1
fi

# 检查API Key配置（支持多种模型提供商）
api_key_configured=false
provider="openai"

# 检查新的统一配置
if [ -n "$LLM_PROVIDER" ]; then
    provider="$LLM_PROVIDER"
    echo "🤖 使用模型提供商: $provider"
fi

if [ -n "$API_KEY" ]; then
    echo "✅ 检测到系统环境变量中的API Key ($provider)"
    api_key_configured=true
elif [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ 检测到系统环境变量中的OpenAI API Key"
    api_key_configured=true
elif [ -n "$openai_api_key" ]; then
    echo "✅ 检测到系统环境变量中的API Key (小写)"
    export OPENAI_API_KEY="$openai_api_key"
    api_key_configured=true
elif grep -q "API_KEY=" .env 2>/dev/null; then
    echo "✅ 检测到.env文件中的API Key配置 ($provider)"
    api_key_configured=true
elif grep -q "OPENAI_API_KEY_FILE=" .env 2>/dev/null; then
    key_file=$(grep "OPENAI_API_KEY_FILE=" .env | cut -d'=' -f2)
    if [ -f "$key_file" ]; then
        echo "✅ 检测到API Key文件配置: $key_file"
        api_key_configured=true
    fi
elif grep -q "API_KEY_FILE=" .env 2>/dev/null; then
    key_file=$(grep "API_KEY_FILE=" .env | cut -d'=' -f2)
    if [ -f "$key_file" ]; then
        echo "✅ 检测到API Key文件配置: $key_file ($provider)"
        api_key_configured=true
    fi
elif grep -q "OPENAI_API_KEY_BASE64=" .env 2>/dev/null; then
    echo "✅ 检测到Base64编码的API Key配置"
    api_key_configured=true
elif grep -q "API_KEY_BASE64=" .env 2>/dev/null; then
    echo "✅ 检测到Base64编码的API Key配置 ($provider)"
    api_key_configured=true
elif python -c "import keyring; exit(0 if keyring.get_password('rag-kb', 'openai_api_key') else 1)" 2>/dev/null; then
    echo "✅ 检测到系统密钥环中的API Key"
    api_key_configured=true
elif grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  检测到.env文件中的明文OpenAI API Key (不推荐)"
    echo "💡 建议使用更安全的方式，参考 SETUP_API_KEY.md"
    api_key_configured=true
fi

if [ "$api_key_configured" = false ]; then
    echo "❌ 未找到API Key配置"
    echo ""
    echo "🔐 快速配置方法:"
    echo "   1. DeepSeek (推荐): cp .env.deepseek .env && 编辑.env文件"
    echo "   2. 智谱AI: cp .env.zhipu .env && 编辑.env文件"
    echo "   3. 系统环境变量: export API_KEY='your-key'"
    echo "   4. 查看详细指南: cat SETUP_API_KEY.md"
    echo ""
    exit 1
fi

# 选择启动模式
echo "请选择启动模式:"
echo "1) 本地开发模式"
echo "2) Docker模式"
echo "3) Docker开发模式"
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo "🔧 启动本地开发模式..."
        
        # 检查Python环境
        if ! command -v python &> /dev/null; then
            echo "❌ Python未安装或未找到"
            exit 1
        fi
        
        # 检查虚拟环境
        if [ ! -d "venv" ]; then
            echo "🔨 创建虚拟环境..."
            python -m venv venv
        fi
        
        # 激活虚拟环境
        echo "🔨 激活虚拟环境..."
        source venv/bin/activate
        
        # 安装依赖
        echo "📦 安装依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
        
        # 创建数据目录
        mkdir -p data/uploads data/chroma_db logs
        
        # 启动后端服务（后台）
        echo "🚀 启动后端服务..."
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > backend.pid
        
        # 等待后端启动
        echo "⏳ 等待后端服务启动..."
        sleep 5
        
        # 检查后端健康状态
        if curl -s http://localhost:8000/health > /dev/null; then
            echo "✅ 后端服务启动成功"
        else
            echo "❌ 后端服务启动失败"
            kill $BACKEND_PID 2>/dev/null || true
            exit 1
        fi
        
        # 启动前端服务
        echo "🎨 启动前端服务..."
        export BACKEND_URL=http://localhost:8000
        streamlit run frontend/streamlit_app.py --server.port 8501
        ;;
        
    2)
        echo "🐳 启动Docker模式..."
        
        # 检查Docker
        if ! command -v docker &> /dev/null; then
            echo "❌ Docker未安装或未找到"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ Docker Compose未安装或未找到"
            exit 1
        fi
        
        # 构建并启动服务
        cd docker
        docker-compose up -d --build
        
        echo "⏳ 等待服务启动..."
        sleep 10
        
        # 检查服务状态
        docker-compose ps
        
        echo "✅ Docker服务启动完成"
        echo "🌐 前端地址: http://localhost:8501"
        echo "🔗 后端API: http://localhost:8000"
        echo "📚 API文档: http://localhost:8000/docs"
        ;;
        
    3)
        echo "🐳 启动Docker开发模式..."
        
        # 检查Docker
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ Docker Compose未安装或未找到"
            exit 1
        fi
        
        # 启动开发模式
        cd docker
        docker-compose -f docker-compose.dev.yml up -d --build
        
        echo "⏳ 等待服务启动..."
        sleep 10
        
        # 检查服务状态
        docker-compose -f docker-compose.dev.yml ps
        
        echo "✅ Docker开发模式启动完成"
        echo "🌐 前端地址: http://localhost:8501"
        echo "🔗 后端API: http://localhost:8000"
        echo "🔄 支持代码热重载"
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 RAG知识库系统启动完成!"
echo "📖 使用指南:"
echo "   1. 访问前端界面上传文档"
echo "   2. 等待文档处理完成"
echo "   3. 开始智能问答"
echo ""
echo "🛑 停止服务:"
if [ "$choice" = "1" ]; then
    echo "   - 按Ctrl+C停止前端"
    echo "   - 运行: kill \$(cat backend.pid) 停止后端"
else
    echo "   - 运行: docker-compose down"
fi