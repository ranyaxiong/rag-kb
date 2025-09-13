#!/usr/bin/env python3
"""
测试新的异步上传功能
"""
import requests
import json
import time
import os

def test_async_upload():
    """测试异步上传"""
    
    # 找到一个PDF文件
    pdf_files = []
    for root, dirs, files in os.walk("data/uploads"):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print("未找到PDF文件用于测试")
        return
    
    test_file = pdf_files[0]
    print(f"测试文件: {os.path.basename(test_file)}")
    
    # 测试异步上传
    print("\n=== 测试异步上传 ===")
    
    with open(test_file, 'rb') as f:
        files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
        
        start_time = time.time()
        response = requests.post(
            "http://localhost:8001/api/documents/upload-async",
            files=files,
            timeout=30  # 异步上传应该很快返回
        )
        end_time = time.time()
        
        print(f"响应时间: {end_time - start_time:.2f} 秒")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 异步上传成功!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            document_id = result.get('document_id')
            if document_id:
                print(f"\n文档ID: {document_id}")
                
                # 测试状态查询
                print("\n=== 测试状态查询 ===")
                for i in range(3):
                    time.sleep(2)  # 等待2秒
                    status_response = requests.get(
                        f"http://localhost:8001/api/documents/status/{document_id}",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        status = status_result.get('status', 'unknown')
                        print(f"第{i+1}次查询: {status}")
                        
                        if status == 'completed':
                            print("🎉 处理完成!")
                            chunk_count = status_result.get('chunk_count', 0)
                            print(f"分块数量: {chunk_count}")
                            break
                        elif status == 'processing':
                            print("🔄 仍在处理中...")
                    else:
                        print(f"❌ 状态查询失败: {status_response.text}")
                        break
        else:
            print(f"❌ 异步上传失败: {response.status_code}")
            print(response.text)

def test_server_health():
    """测试服务器健康状态"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器健康")
            return True
        else:
            print(f"❌ 服务器状态异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接服务器: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== 异步上传功能测试 ===")
    
    if test_server_health():
        test_async_upload()
    else:
        print("请确保服务器在http://localhost:8001运行")