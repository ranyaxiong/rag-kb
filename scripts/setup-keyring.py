#!/usr/bin/env python3
"""
系统密钥环设置脚本
"""
import getpass
import sys

try:
    import keyring
except ImportError:
    print("❌ keyring库未安装")
    print("请运行: pip install keyring")
    sys.exit(1)

def main():
    print("🔐 RAG知识库 - 系统密钥环设置")
    print("这将把您的OpenAI API Key安全地存储在系统密钥环中")
    print("")
    
    # 检查是否已有密钥
    existing_key = keyring.get_password("rag-kb", "openai_api_key")
    if existing_key:
        print("ℹ️  检测到已存储的API Key")
        overwrite = input("是否覆盖现有密钥? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("操作取消")
            return
    
    # 获取API Key
    while True:
        api_key = getpass.getpass("请输入您的OpenAI API Key: ").strip()
        
        if not api_key:
            print("❌ API Key不能为空")
            continue
        
        if not api_key.startswith("sk-"):
            print("⚠️  警告: OpenAI API Key通常以 'sk-' 开头")
            confirm = input("继续使用这个密钥吗? (y/N): ").lower().strip()
            if confirm != 'y':
                continue
        
        # 确认密钥
        confirm_key = getpass.getpass("请再次输入API Key确认: ").strip()
        
        if api_key != confirm_key:
            print("❌ 两次输入的密钥不一致，请重新输入")
            continue
        
        break
    
    try:
        # 存储密钥
        keyring.set_password("rag-kb", "openai_api_key", api_key)
        print("✅ API Key已安全存储到系统密钥环")
        print("")
        print("📝 现在您可以启动应用，系统会自动从密钥环读取API Key")
        print("💡 使用方式:")
        print("   - 确保.env文件中没有设置OPENAI_API_KEY")
        print("   - 运行: ./scripts/start.sh")
        print("")
        print("🔍 验证存储:")
        test_key = keyring.get_password("rag-kb", "openai_api_key")
        if test_key:
            print(f"   密钥长度: {len(test_key)} 字符")
            print(f"   密钥前缀: {test_key[:7]}...")
        
    except Exception as e:
        print(f"❌ 存储密钥时发生错误: {str(e)}")
        sys.exit(1)

def delete_key():
    """删除存储的密钥"""
    try:
        existing_key = keyring.get_password("rag-kb", "openai_api_key")
        if not existing_key:
            print("ℹ️  未找到存储的API Key")
            return
        
        confirm = input("确认删除存储的API Key? (y/N): ").lower().strip()
        if confirm == 'y':
            keyring.delete_password("rag-kb", "openai_api_key")
            print("✅ API Key已从系统密钥环删除")
        else:
            print("操作取消")
            
    except Exception as e:
        print(f"❌ 删除密钥时发生错误: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        delete_key()
    else:
        main()