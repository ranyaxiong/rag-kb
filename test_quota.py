#!/usr/bin/env python3
"""
配额功能测试脚本
"""
import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

def test_quota_functionality():
    """测试配额功能"""
    
    print("🧪 开始测试配额功能...")
    print("=" * 50)
    
    # 1. 获取配额信息
    print("\n1️⃣ 获取配额信息:")
    try:
        response = requests.get(f"{BACKEND_URL}/api/qa/quota")
        if response.status_code == 200:
            quota_info = response.json()
            print(f"✅ 配额信息: {json.dumps(quota_info, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 获取配额失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取配额出错: {e}")
    
    # 2. 测试问答请求（模拟用尽配额）
    print("\n2️⃣ 连续提问测试（模拟用尽配额）:")
    test_question = "这个系统是做什么的？"
    
    for i in range(7):  # 超过默认配额5次
        print(f"\n📝 第 {i+1} 次提问:")
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/qa/ask",
                json={"question": test_question},
                headers={"User-Agent": "quota-test-client"}
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "")
                
                # 检查是否是配额限制消息
                if "配额已用完" in answer or "🚫" in answer:
                    print(f"⚠️  配额限制触发: {answer[:100]}...")
                    break
                else:
                    print(f"✅ 正常回答: {answer[:100]}...")
            else:
                print(f"❌ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 请求出错: {e}")
        
        time.sleep(1)  # 避免请求过快
    
    # 3. 测试使用自定义API Key（应该绕过配额限制）
    print("\n3️⃣ 测试自定义API Key（绕过配额）:")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/qa/ask",
            json={"question": test_question},
            headers={
                "Authorization": "Bearer fake-api-key-for-test",
                "X-LLM-Provider": "openai",
                "User-Agent": "quota-test-client"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            print(f"✅ 自定义Key回答: {answer[:100]}...")
        else:
            print(f"⚠️  自定义Key失败（预期，因为是假Key）: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 自定义Key测试出错: {e}")
    
    # 4. 获取最终配额状态
    print("\n4️⃣ 最终配额状态:")
    try:
        response = requests.get(f"{BACKEND_URL}/api/qa/quota")
        if response.status_code == 200:
            quota_info = response.json()
            print(f"✅ 最终配额: {json.dumps(quota_info, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 获取配额失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取配额出错: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 配额功能测试完成!")
    print("\n💡 提示:")
    print("- 如果配额功能正常工作，第5-7次提问应该返回配额限制消息")
    print("- 前端界面会显示实时的配额使用情况")
    print("- 管理员可以使用 /api/qa/quota/reset?admin_key=admin123 重置配额")

if __name__ == "__main__":
    test_quota_functionality()