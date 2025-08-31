#!/bin/bash
# 设置OpenAI API Key到系统环境变量

echo "🔐 设置OpenAI API Key到系统环境变量"
echo ""

read -p "请输入你的OpenAI API Key: " api_key

if [ -z "$api_key" ]; then
    echo "❌ API Key不能为空"
    exit 1
fi

echo ""
echo "🔧 正在设置环境变量..."

# 检测shell类型并添加到相应的配置文件
if [ -n "$ZSH_VERSION" ]; then
    # Zsh
    config_file="$HOME/.zshrc"
    shell_name="Zsh"
elif [ -n "$BASH_VERSION" ]; then
    # Bash
    config_file="$HOME/.bashrc"
    shell_name="Bash"
else
    # 默认使用 .bashrc
    config_file="$HOME/.bashrc"
    shell_name="Bash"
fi

# 检查是否已经存在配置
if grep -q "export OPENAI_API_KEY=" "$config_file" 2>/dev/null; then
    echo "⚠️  发现现有的API Key配置，正在更新..."
    # 使用sed替换现有配置
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/export OPENAI_API_KEY=.*/export OPENAI_API_KEY=\"$api_key\"/" "$config_file"
    else
        # Linux
        sed -i "s/export OPENAI_API_KEY=.*/export OPENAI_API_KEY=\"$api_key\"/" "$config_file"
    fi
else
    # 添加新配置
    echo "" >> "$config_file"
    echo "# OpenAI API Key for RAG Knowledge Base" >> "$config_file"
    echo "export OPENAI_API_KEY=\"$api_key\"" >> "$config_file"
fi

# 立即导出到当前会话
export OPENAI_API_KEY="$api_key"

echo "✅ API Key已成功设置到 $shell_name 配置文件: $config_file"
echo "📝 变量名: OPENAI_API_KEY"
echo "🔄 请运行 'source $config_file' 或重新打开终端以使环境变量生效"
echo ""
echo "💡 现在你可以运行 ./scripts/start.sh 启动服务"
echo ""

# 验证设置
echo "🔍 验证API Key设置:"
if [ ${#OPENAI_API_KEY} -gt 10 ]; then
    echo "   ✅ API Key长度: ${#OPENAI_API_KEY} 字符"
    echo "   ✅ 前缀: ${OPENAI_API_KEY:0:8}..."
else
    echo "   ⚠️  API Key可能不正确"
fi