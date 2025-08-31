# 模型配置指南

本系统支持多种大语言模型提供商，包括OpenAI、DeepSeek、智谱AI等。以下是配置方法：

## 支持的模型提供商

- **OpenAI**: GPT-3.5/4，text-embedding-ada-002
- **DeepSeek**: deepseek-chat，兼容OpenAI embedding
- **智谱AI (GLM)**: glm-4，embedding-2
- 更多模型提供商可轻松扩展...

## 快速配置

### 使用DeepSeek（推荐，免费额度大）

1. 访问 [DeepSeek平台](https://platform.deepseek.com) 获取API Key
2. 复制配置文件：
   ```bash
   cp .env.deepseek .env
   ```
3. 编辑 `.env` 文件，填入你的DeepSeek API Key：
   ```
   API_KEY=sk-your-deepseek-api-key-here
   ```

### 使用智谱AI

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn) 获取API Key
2. 复制配置文件：
   ```bash
   cp .env.zhipu .env
   ```
3. 编辑 `.env` 文件，填入你的智谱AI API Key

### 使用OpenAI

1. 访问 [OpenAI平台](https://platform.openai.com/api-keys) 获取API Key
2. 设置环境变量（见下方详细方法）

## 方法一：使用自动化脚本（推荐）

### Windows用户
```cmd
scripts\setup-env-windows.bat
```

### Linux/Mac用户  
```bash
./scripts/setup-env.sh
```

## 方法二：手动设置系统环境变量

### Windows
1. 右键点击"此电脑" → "属性"
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"用户变量"中点击"新建"
5. 添加以下变量：
   - 变量名：`LLM_PROVIDER`，变量值：`deepseek` (或 `openai`、`zhipu`)
   - 变量名：`API_KEY`，变量值：你的API Key
6. 重启命令提示符

### Linux/Mac
在 `~/.bashrc` 或 `~/.zshrc` 中添加：
```bash
export LLM_PROVIDER="deepseek"  # 或 openai, zhipu
export API_KEY="your-api-key-here"
```

然后运行：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 方法三：临时设置（仅当前会话有效）

### Windows
```cmd
set LLM_PROVIDER=deepseek
set API_KEY=your-api-key-here
```

### Linux/Mac
```bash
export LLM_PROVIDER="deepseek"
export API_KEY="your-api-key-here"
```

## 获取API Key

### DeepSeek
1. 访问 [DeepSeek平台](https://platform.deepseek.com)
2. 注册登录账户
3. 在API Keys页面创建新的API Key
4. 复制API Key（格式：`sk-...`）

### 智谱AI (GLM)
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn)
2. 注册登录账户
3. 在API Keys页面创建新的API Key
4. 复制API Key

### OpenAI
1. 访问 [OpenAI API Keys](https://platform.openai.com/api-keys)
2. 登录账户
3. 点击"Create new secret key"
4. 复制API Key（格式：`sk-...`）

## 验证设置

设置完成后，运行启动脚本：
```bash
./scripts/start.sh
```

如果看到"✅ 检测到系统环境变量中的API Key"，说明设置成功。

## 高级配置

如需自定义模型参数，可以在 `.env` 文件中设置：
```bash
# 自定义聊天模型
CHAT_MODEL=deepseek-chat

# 自定义嵌入模型
EMBEDDING_MODEL=text-embedding-ada-002

# 自定义API端点
API_BASE_URL=https://api.deepseek.com

# 其他参数
CHUNK_SIZE=1000
MAX_SOURCES=3
```

## 安全提醒

- ⚠️ **不要**将API Key提交到代码仓库
- ⚠️ **不要**在公共场所显示API Key
- ✅ 使用环境变量或`.env`文件是推荐的安全做法
- ✅ 定期轮换你的API Key
- ✅ DeepSeek等国产模型通常有更大的免费额度