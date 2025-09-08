#!/usr/bin/env python3
"""
CORS配置设置脚本
用于快速配置生产环境的CORS安全设置
"""
import os
import sys
from urllib.parse import urlparse

def validate_url(url):
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def setup_cors_config():
    """交互式CORS配置设置"""
    print("🔒 RAG知识库 CORS安全配置")
    print("=" * 50)
    print()
    
    # 获取当前配置
    current_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501")
    print(f"当前CORS配置: {current_origins}")
    print()
    
    # 询问部署环境
    print("请选择部署环境:")
    print("1. 开发环境 (localhost)")
    print("2. 生产环境 (自定义域名)")
    print("3. 混合环境 (localhost + 自定义域名)")
    
    choice = input("选择 (1-3): ").strip()
    
    origins = []
    
    if choice == "1":
        # 开发环境
        origins = [
            "http://localhost:8501",
            "http://127.0.0.1:8501"
        ]
        print("✅ 已配置开发环境CORS设置")
        
    elif choice == "2":
        # 生产环境
        print("\n请输入你的域名 (支持多个域名，用逗号分隔):")
        print("示例: https://yourdomain.com,https://www.yourdomain.com")
        domains_input = input("域名: ").strip()
        
        if domains_input:
            for domain in domains_input.split(","):
                domain = domain.strip()
                if validate_url(domain):
                    origins.append(domain)
                else:
                    print(f"⚠️  无效的URL格式: {domain}")
        
        if not origins:
            print("❌ 没有有效的域名，使用默认配置")
            origins = ["http://localhost:8501"]
        else:
            print(f"✅ 已配置生产环境CORS设置: {', '.join(origins)}")
            
    elif choice == "3":
        # 混合环境
        origins = [
            "http://localhost:8501",
            "http://127.0.0.1:8501"
        ]
        
        print("\n请输入生产域名 (支持多个域名，用逗号分隔):")
        domains_input = input("域名: ").strip()
        
        if domains_input:
            for domain in domains_input.split(","):
                domain = domain.strip()
                if validate_url(domain):
                    origins.append(domain)
                else:
                    print(f"⚠️  无效的URL格式: {domain}")
        
        print(f"✅ 已配置混合环境CORS设置: {', '.join(origins)}")
    else:
        print("❌ 无效选择，使用默认配置")
        origins = ["http://localhost:8501"]
    
    # 生成配置
    origins_str = ",".join(origins)
    
    # 写入.env文件
    env_path = ".env"
    env_content = []
    
    # 读取现有配置
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.readlines()
    
    # 更新CORS配置
    cors_found = False
    for i, line in enumerate(env_content):
        if line.startswith("ALLOWED_ORIGINS="):
            env_content[i] = f"ALLOWED_ORIGINS={origins_str}\n"
            cors_found = True
            break
    
    if not cors_found:
        env_content.append(f"ALLOWED_ORIGINS={origins_str}\n")
    
    # 确保其他CORS配置存在
    methods_found = False
    headers_found = False
    
    for line in env_content:
        if line.startswith("ALLOWED_METHODS="):
            methods_found = True
        elif line.startswith("ALLOWED_HEADERS="):
            headers_found = True
    
    if not methods_found:
        env_content.append("ALLOWED_METHODS=GET,POST,DELETE\n")
    if not headers_found:
        env_content.append("ALLOWED_HEADERS=Content-Type,Authorization\n")
    
    # 写入文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(env_content)
    
    print()
    print("📝 配置已保存到 .env 文件")
    print(f"   ALLOWED_ORIGINS={origins_str}")
    print("   ALLOWED_METHODS=GET,POST,DELETE")
    print("   ALLOWED_HEADERS=Content-Type,Authorization")
    print()
    print("🔄 请重启服务以应用新配置:")
    print("   make restart")
    print("   或者 docker-compose restart")

def show_current_config():
    """显示当前CORS配置"""
    print("📋 当前CORS配置:")
    print("-" * 30)
    
    origins = os.getenv("ALLOWED_ORIGINS", "未设置")
    methods = os.getenv("ALLOWED_METHODS", "未设置")
    headers = os.getenv("ALLOWED_HEADERS", "未设置")
    
    print(f"允许的源域名: {origins}")
    print(f"允许的HTTP方法: {methods}")
    print(f"允许的请求头: {headers}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_current_config()
    else:
        setup_cors_config()