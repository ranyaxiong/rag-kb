import getpass
from pwdlib import PasswordHash


def generate_hash():
    """
    一个交互式脚本，用于安全地生成密码哈希。
    """
    try:
        print("--- 密码哈希生成工具 ---")
        # 使用 getpass 可以在输入密码时不显示字符，更安全
        password = getpass.getpass("请输入要哈希的管理员密码: ")
        
        if not password:
            print("错误：密码不能为空。")
            return

        confirm_password = getpass.getpass("请再次输入密码以确认: ")

        if password != confirm_password:
            print("错误：两次输入的密码不匹配。")
            return

        # 使用 pwdlib 生成哈希
        ph = PasswordHash.recommended()
        hashed_password = ph.hash(password)

        print("\n✅ 密码哈希已成功生成！")
        print("请将以下生成的哈希值，配置到您的生产环境的环境变量中。")
        print("-" * 30)
        print(f"ADMIN_PASSWORD_HASH={hashed_password}")
        print("-" * 30)
        print("\n**安全提示**: 不要将此哈希值硬编码或提交到代码库中。")

    except Exception as e:
        print(f"\n发生错误: {e}")

if __name__ == "__main__":
    generate_hash()