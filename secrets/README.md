# 安全密钥管理指南

这个目录用于存放敏感的API密钥文件。所有文件都会被Git忽略，确保密钥不会意外提交到代码库。

## 📋 支持的密钥管理方式

### 1. 系统环境变量 (推荐)

最安全的方式是在系统级别设置环境变量：

```bash
# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"

# Windows
set OPENAI_API_KEY=your-api-key-here
# 或永久设置
setx OPENAI_API_KEY "your-api-key-here"
```

### 2. 密钥文件存储

创建一个密钥文件，应用会从文件读取：

```bash
# 创建密钥文件
echo "your-api-key-here" > secrets/openai_api_key.txt

# 设置环境变量指向文件
export OPENAI_API_KEY_FILE="./secrets/openai_api_key.txt"
```

### 3. Base64编码环境变量

对API key进行base64编码后存储：

```bash
# 编码API key
API_KEY_ENCODED=$(echo -n "your-api-key-here" | base64)

# 设置编码后的环境变量
export OPENAI_API_KEY_BASE64="$API_KEY_ENCODED"
```

### 4. Docker Secrets (生产环境推荐)

在Docker Swarm或Kubernetes中使用secrets：

```bash
# 创建Docker secret
echo "your-api-key-here" | docker secret create openai_api_key -

# 在docker-compose中使用
docker-compose -f docker-compose.secrets.yml up -d
```

### 5. 系统密钥环 (Linux/Mac)

使用系统的密钥管理服务：

```bash
# 安装keyring (如果需要)
pip install keyring

# 存储密钥
python -c "import keyring; keyring.set_password('rag-kb', 'openai_api_key', 'your-api-key-here')"
```

## 🔐 安全等级排序

从最安全到最不安全：

1. **🥇 系统密钥环** - 操作系统级加密存储
2. **🥈 Docker Secrets** - 容器编排平台的密钥管理
3. **🥉 系统环境变量** - 系统级别，不写入文件
4. **🏅 加密密钥文件** - 本地加密文件存储
5. **⚠️ Base64环境变量** - 简单编码，不是真正的加密
6. **❌ .env明文文件** - 最不安全，仅开发使用

## 📝 使用示例

### 开发环境
```bash
# 方式1: 系统环境变量
export OPENAI_API_KEY="sk-your-key"
./scripts/start.sh

# 方式2: 密钥文件
echo "sk-your-key" > secrets/openai_api_key.txt
export OPENAI_API_KEY_FILE="./secrets/openai_api_key.txt"
./scripts/start.sh
```

### 生产环境
```bash
# 使用Docker secrets
echo "sk-your-key" > secrets/openai_api_key.txt
docker-compose -f docker/docker-compose.secrets.yml up -d
```

### CI/CD环境
在GitHub Actions中使用Secrets：

1. 在GitHub仓库设置中添加Secret: `OPENAI_API_KEY`
2. 在workflow中使用: `${{ secrets.OPENAI_API_KEY }}`

## ⚠️ 重要安全提醒

1. **永远不要提交密钥到Git**
2. **定期轮换API密钥**
3. **限制API密钥的使用范围**
4. **监控API密钥的使用情况**
5. **使用最小权限原则**

## 🚨 如果密钥泄露了怎么办？

1. **立即撤销泄露的API密钥**
2. **生成新的API密钥**
3. **检查使用日志，确认是否有异常调用**
4. **更新所有使用该密钥的服务**
5. **审查访问控制和安全措施**