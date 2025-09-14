#!/usr/bin/env python3
"""
测试doc_processor导入修复
"""

def test_doc_processor_import():
    """测试doc_processor导入是否正常"""
    print("=== 测试doc_processor导入修复 ===")
    
    try:
        # 测试从document_processor模块导入doc_processor
        from app.core.document_processor import doc_processor
        print("✅ 成功导入doc_processor")
        print(f"   类型: {type(doc_processor)}")
        print(f"   支持的文件类型: {doc_processor.supported_extensions}")
        
        # 测试基本方法
        test_filename = "test.pdf"
        is_supported = doc_processor.is_supported_file(test_filename)
        print(f"   PDF文件支持检查: {is_supported}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_async_processor_import():
    """测试async_processor中的导入是否正常"""
    print("\n=== 测试async_processor中的导入 ===")
    
    try:
        # 模拟async_processor中的导入
        from app.core.document_processor import doc_processor
        from app.core.vector_store import get_vector_store
        from app.core.job_status import job_status
        
        print("✅ async_processor相关导入成功")
        print(f"   doc_processor: {type(doc_processor)}")
        print(f"   get_vector_store: {get_vector_store}")
        print(f"   job_status: {type(job_status)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    success1 = test_doc_processor_import()
    success2 = test_async_processor_import()
    
    if success1 and success2:
        print("\n🎉 所有导入测试通过！修复成功！")
    else:
        print("\n❌ 仍有导入问题需要解决")
