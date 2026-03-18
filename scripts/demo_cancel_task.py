#!/usr/bin/env python
"""
任务取消功能演示脚本

演示如何使用API取消正在处理的文档任务
"""
import requests
import time
import sys
from pathlib import Path


class CancelTaskDemo:
    """任务取消演示类"""
    
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
    
    def upload_document(self, file_path: str):
        """上传文档并返回document_id"""
        print(f"\n📤 上传文档: {file_path}")
        
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{self.backend_url}/api/documents/upload-async",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            document_id = result.get('document_id')
            print(f"✅ 上传成功! Document ID: {document_id}")
            return document_id
        else:
            print(f"❌ 上传失败: {response.text}")
            return None
    
    def check_status(self, document_id: str):
        """查询任务状态"""
        response = requests.get(
            f"{self.backend_url}/api/documents/status/{document_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('status', 'unknown')
            progress = result.get('progress', 0)
            message = result.get('message', '')
            
            print(f"📊 状态: {status} | 进度: {progress}% | {message}")
            return result
        else:
            print(f"❌ 查询状态失败: {response.text}")
            return None
    
    def check_cancellable(self, document_id: str):
        """查询任务是否可取消"""
        response = requests.get(
            f"{self.backend_url}/api/documents/cancel-status/{document_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            cancellable = result.get('cancellable', False)
            status = result.get('status', 'unknown')
            
            print(f"🔍 任务状态: {status} | 可取消: {'是' if cancellable else '否'}")
            return cancellable
        else:
            print(f"❌ 查询失败: {response.text}")
            return False
    
    def cancel_task(self, document_id: str):
        """取消任务"""
        print(f"\n🛑 发送取消请求...")
        
        response = requests.post(
            f"{self.backend_url}/api/documents/cancel/{document_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ {result.get('message')}")
                print(f"📝 状态: {result.get('status')}")
                return True
            else:
                print(f"⚠️ {result.get('message')}")
                return False
        else:
            print(f"❌ 取消失败: {response.text}")
            return False
    
    def demo_cancel_immediately(self, file_path: str):
        """演示：上传后立即取消"""
        print("\n" + "="*60)
        print("演示场景 1: 上传后立即取消")
        print("="*60)
        
        # 上传文档
        document_id = self.upload_document(file_path)
        if not document_id:
            return
        
        # 立即取消
        time.sleep(0.5)  # 短暂延迟
        self.cancel_task(document_id)
        
        # 检查最终状态
        time.sleep(1)
        self.check_status(document_id)
    
    def demo_cancel_during_processing(self, file_path: str):
        """演示：处理过程中取消"""
        print("\n" + "="*60)
        print("演示场景 2: 处理过程中取消")
        print("="*60)
        
        # 上传文档
        document_id = self.upload_document(file_path)
        if not document_id:
            return
        
        # 等待任务开始处理
        print("\n⏳ 等待任务开始处理...")
        for i in range(5):
            time.sleep(1)
            status = self.check_status(document_id)
            if status and status.get('status') == 'processing':
                break
        
        # 检查是否可取消
        if self.check_cancellable(document_id):
            # 取消任务
            self.cancel_task(document_id)
            
            # 检查最终状态
            time.sleep(2)
            self.check_status(document_id)
        else:
            print("⚠️ 任务不可取消（可能已完成）")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python demo_cancel_task.py <文件路径> [场景]")
        print("\n场景选项:")
        print("  1 - 上传后立即取消（默认）")
        print("  2 - 处理过程中取消")
        print("\n示例:")
        print("  python demo_cancel_task.py test.pdf 1")
        sys.exit(1)
    
    file_path = sys.argv[1]
    scenario = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    demo = CancelTaskDemo()
    
    if scenario == 1:
        demo.demo_cancel_immediately(file_path)
    elif scenario == 2:
        demo.demo_cancel_during_processing(file_path)
    else:
        print(f"❌ 未知场景: {scenario}")
        sys.exit(1)


if __name__ == "__main__":
    main()

