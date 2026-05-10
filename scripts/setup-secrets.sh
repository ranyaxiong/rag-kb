#!/bin/bash
# Docker Secrets设置脚本

set -e

echo "🔐 Docker Secrets设置向导"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装或未找到"
    exit 1
fi

# 创建secrets目录
mkdir -p secrets

echo "请选择密钥设置方式:"
echo "1) 手动输入API Key"
echo "2) 从现有.env文件读取"
echo "3) 从系统环境变量读取"
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo "请输入您的OpenAI API Key:"
        read -s api_key
        echo ""
        
        if [ -z "$api_key" ]; then
            echo "❌ API Key不能为空"
            exit 1
        fi
        
        echo "$api_key" > secrets/openai_api_key
        ;;
        
    2)
        if [ ! -f .env ]; then
            echo "❌ .env文件不存在"
            exit 1
        fi
        
        api_key=$(grep "OPENAI_API_KEY=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        
        if [ -z "$api_key" ]; then
            echo "❌ 在.env文件中未找到OPENAI_API_KEY"
            exit 1
        fi
        
        echo "$api_key" > secrets/openai_api_key
        ;;
        
    3)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "❌ 系统环境变量OPENAI_API_KEY未设置"
            exit 1
        fi
        
        echo "$OPENAI_API_KEY" > secrets/openai_api_key
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 设置文件权限
chmod 600 secrets/openai_api_key

echo "✅ Docker Secret文件已创建: secrets/openai_api_key"
echo "🔒 文件权限已设置为600 (仅所有者可读写)"
echo ""
echo "🐳 现在您可以使用Docker Secrets启动应用:"
echo "   cd docker"
echo "   docker-compose -f docker-compose.secrets.yml up -d"
echo ""
echo "⚠️  重要提醒:"
echo "   - secrets/目录下的所有文件都会被Git忽略"
echo "   - 请妥善保管密钥文件的备份"
echo "   - 定期轮换您的API密钥"