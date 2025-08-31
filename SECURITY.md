# 🔐 安全配置指南

## API Key安全管理

为了保护您的OpenAI API Key，我们提供了多种安全的存储方式。**强烈建议不要将API Key明文存储在.env文件中**。

## 🛡️ 推荐的安全方案

### 1. 系统环境变量 (★★★★★ 推荐)

在操作系统级别设置环境变量，不写入任何文件：

**Windows:**
```powershell
# 临时设置（当前会话）
$env:OPENAI_API_KEY = "your-api-key-here"

# 永久设置
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-api-key-here", "User")
```

**Linux/Mac:**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export OPENAI_API_KEY="your-api-key-here"

# 重新加载配置
source ~/.bashrc
```

### 2. 系统密钥环 (★★★★★ 最安全)

使用操作系统的密钥管理服务：

```bash
# 安装keyring
pip install keyring

# 设置密钥
python scripts/setup-keyring.py

# 删除密钥
python scripts/setup-keyring.py delete
```

### 3. Docker Secrets (★★★★☆ 生产推荐)

适用于生产环境的Docker部署：

```bash
# 设置Docker secrets
./scripts/setup-secrets.sh

# 使用secrets启动
cd docker
docker-compose -f docker-compose.secrets.yml up -d
```

### 4. 加密文件存储 (★★★☆☆)

将API Key存储在单独的文件中，设置严格的文件权限：

```bash
# 创建密钥文件
echo "your-api-key-here" > secrets/openai_api_key.txt
chmod 600 secrets/openai_api_key.txt

# 配置环境变量
export OPENAI_API_KEY_FILE="./secrets/openai_api_key.txt"
```

## 🚀 启动应用（安全方式）

### 方式1: 系统环境变量
```bash
export OPENAI_API_KEY="your-key"
./scripts/start.sh
```

### 方式2: 密钥文件
```bash
export OPENAI_API_KEY_FILE="./secrets/openai_api_key.txt"
./scripts/start.sh
```

### 方式3: Docker Secrets
```bash
cd docker
docker-compose -f docker-compose.secrets.yml up -d
```

### 方式4: 系统密钥环
```bash
# 无需额外设置，应用会自动检测
./scripts/start.sh
```

## 🔍 安全检查清单

### 开发环境
- [ ] 确保.env文件在.gitignore中
- [ ] 不要在代码中硬编码API Key
- [ ] 使用系统环境变量或密钥环
- [ ] 定期检查Git提交历史

### 生产环境  
- [ ] 使用Docker Secrets或云平台密钥管理服务
- [ ] 启用API Key轮换策略
- [ ] 监控API使用情况和异常调用
- [ ] 设置访问日志和审计

### 团队协作
- [ ] 每个团队成员使用自己的API Key
- [ ] 在文档中明确密钥管理政策
- [ ] 定期进行安全培训和检查
- [ ] 建立密钥泄露应急预案

## 🚨 如果发现密钥泄露

1. **立即行动**
   ```bash
   # 撤销泄露的密钥
   # 在OpenAI控制台中删除API Key
   
   # 生成新的密钥
   # 在OpenAI控制台中创建新的API Key
   ```

2. **检查影响范围**
   - 查看OpenAI使用日志
   - 检查是否有异常API调用
   - 确认哪些服务受到影响

3. **更新系统**
   ```bash
   # 更新所有使用该密钥的服务
   python scripts/setup-keyring.py  # 存储新密钥
   
   # 重启服务
   ./scripts/stop.sh
   ./scripts/start.sh
   ```

4. **预防措施**
   - 审查代码提交历史
   - 更新安全政策
   - 加强访问控制

## 🛠️ 故障排除

### API Key无法读取
```bash
# 检查配置
python -c "
from app.core.config import settings
key = settings.get_openai_api_key()
print('API Key found:', bool(key))
print('Key source: ', end='')
if settings.openai_api_key: print('environment')
elif settings.openai_api_key_file: print('file')
else: print('keyring or other')
"
```

### 权限问题
```bash
# 检查文件权限
ls -la secrets/
ls -la .env*

# 设置正确权限
chmod 600 secrets/*
chmod 600 .env*
```

### Docker Secrets问题
```bash
# 检查secret是否创建成功
docker secret ls

# 检查容器中的secret
docker exec <container-name> ls -la /run/secrets/
```

## 📚 最佳实践

1. **永远不要在代码中硬编码密钥**
2. **使用最小权限原则**
3. **定期轮换API密钥**
4. **监控API使用情况**
5. **启用访问日志**
6. **建立密钥管理流程**
7. **定期安全审计**
8. **团队安全培训**

## 🔗 相关链接

- [OpenAI API Key管理](https://platform.openai.com/api-keys)
- [Docker Secrets文档](https://docs.docker.com/engine/swarm/secrets/)
- [Python keyring库](https://pypi.org/project/keyring/)
- [环境变量最佳实践](https://12factor.net/config)