#!/usr/bin/env python3
"""
测试PDF上传和处理
"""
import requests
import os
import json

def test_pdf_upload():
    """测试PDF上传和处理"""
    
    # 找到最新的PDF文件
    pdf_files = []
    for root, dirs, files in os.walk("data/uploads"):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print("未找到PDF文件")
        return
    
    pdf_files.sort(key=os.path.getmtime, reverse=True)
    latest_pdf = pdf_files[0]
    
    print(f"准备上传PDF: {os.path.basename(latest_pdf)}")
    
    # 上传文件
    url = "http://localhost:8001/api/documents/upload"
    
    with open(latest_pdf, 'rb') as f:
        files = {'file': (os.path.basename(latest_pdf), f, 'application/pdf')}
        
        print("开始上传...")
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 上传成功！")
            print(f"文档ID: {result.get('document_id', 'N/A')}")
            print(f"分块数量: {result.get('chunk_count', 'N/A')}")
            print(f"状态: {result.get('status', 'N/A')}")
            
            if result.get('status') == 'completed':
                print("✓ 文档处理完成")
            else:
                print(f"⚠ 处理状态: {result.get('status')}")
                if 'error_message' in result:
                    print(f"错误信息: {result['error_message']}")
        else:
            print(f"✗ 上传失败: {response.status_code}")
            print(f"错误信息: {response.text}")

if __name__ == "__main__":
    test_pdf_upload()