#!/usr/bin/env python3
"""
测试异步处理修复
"""
import os
import tempfile
import time

def test_async_processing_simulation():
    """模拟异步处理流程"""
    print("=== 测试异步处理流程模拟 ===")
    
    try:
        # 导入必要的模块
        from app.core.document_processor import doc_processor
        from app.core.vector_store import get_vector_store
        from app.core.job_status import job_status
        from app.core.async_processor import async_processor
        
        print("✅ 所有模块导入成功")
        
        # 创建一个临时测试文件
        test_content = """
        这是一个测试文档。
        用于验证异步处理流程是否正常工作。
        包含多行文本内容。
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_file_path = f.name
        
        filename = os.path.basename(temp_file_path)
        print(f"创建临时测试文件: {filename}")
        
        # 测试doc_processor.process_document方法调用
        print("\n--- 测试process_document方法调用 ---")
        try:
            result = doc_processor.process_document(temp_file_path, filename)
            print(f"✅ process_document调用成功")
            print(f"   状态: {result['status']}")
            print(f"   分块数量: {result['chunk_count']}")
            print(f"   文档ID: {result['document_id']}")
            
            if result['status'] == 'completed':
                print("✅ 文档处理成功")
                return True
            else:
                print(f"❌ 文档处理失败: {result.get('error_message')}")
                return False
                
        except Exception as e:
            print(f"❌ process_document调用失败: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_method_signature():
    """测试方法签名"""
    print("\n=== 测试方法签名 ===")
    
    try:
        from app.core.document_processor import doc_processor
        import inspect
        
        # 获取process_document方法的签名
        sig = inspect.signature(doc_processor.process_document)
        params = list(sig.parameters.keys())
        
        print(f"process_document方法参数: {params}")
        
        # 检查是否有正确的参数
        if 'file_path' in params and 'filename' in params:
            print("✅ 方法签名正确")
            return True
        else:
            print("❌ 方法签名不正确")
            return False
            
    except Exception as e:
        print(f"❌ 方法签名检查失败: {e}")
        return False

if __name__ == "__main__":
    success1 = test_method_signature()
    success2 = test_async_processing_simulation()
    
    if success1 and success2:
        print("\n🎉 异步处理修复验证通过！")
    else:
        print("\n❌ 仍有问题需要解决")
