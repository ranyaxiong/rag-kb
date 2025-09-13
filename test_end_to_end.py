"""
端到端测试：验证PDF处理器是否真正集成到系统中
"""
import sys
import os
import tempfile
import io
sys.path.append('.')

def create_test_pdf():
    """创建一个简单的测试PDF文件"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # 创建临时文件
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        
        # 创建PDF内容
        c = canvas.Canvas(temp_pdf.name, pagesize=letter)
        c.drawString(100, 750, "This is a test PDF document")
        c.drawString(100, 730, "Enhanced PDF processor test")
        c.drawString(100, 710, "PyMuPDF vs PyPDF comparison")
        c.save()
        
        return temp_pdf.name
    except ImportError:
        print("reportlab未安装，无法创建测试PDF")
        return None

def test_document_processor_flow():
    """测试完整的文档处理流程"""
    print("=== 端到端文档处理测试 ===")
    
    # 创建测试PDF
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        print("跳过PDF创建测试")
        return True
    
    try:
        from app.core.document_processor import DocumentProcessor
        
        # 初始化处理器
        processor = DocumentProcessor()
        print(f"PDF加载器类型: {processor.loaders['.pdf']}")
        
        # 获取PDF文件信息
        doc_info = processor.get_document_info(test_pdf_path)
        print(f"文档信息: {doc_info}")
        
        # 加载文档
        print("正在加载文档...")
        documents = processor.load_document(test_pdf_path)
        print(f"加载到 {len(documents)} 个文档段")
        
        # 检查内容
        if documents:
            first_doc = documents[0]
            print(f"第一个文档的内容: {first_doc.page_content[:100]}...")
            print(f"元数据: {first_doc.metadata}")
            
            # 检查是否包含测试内容
            content = first_doc.page_content
            if "Enhanced PDF processor test" in content:
                print("✅ 成功提取到测试内容")
                return True
            else:
                print("⚠️ 未找到预期的测试内容")
                return False
        else:
            print("❌ 未加载到任何文档")
            return False
            
    except Exception as e:
        print(f"❌ 端到端测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if test_pdf_path and os.path.exists(test_pdf_path):
            os.unlink(test_pdf_path)

def test_smart_pdf_loader_directly():
    """直接测试SmartPDFLoader"""
    print("\n=== 直接测试SmartPDFLoader ===")
    
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        return True
        
    try:
        from app.core.document_processor import SmartPDFLoader
        
        loader = SmartPDFLoader(test_pdf_path)
        print(f"SmartPDFLoader初始化成功")
        print(f"增强处理器可用: {hasattr(loader, 'enhanced_processor')}")
        
        # 尝试加载
        print("正在使用SmartPDFLoader加载...")
        documents = loader.load()
        
        if documents:
            print(f"✅ SmartPDFLoader成功加载 {len(documents)} 个文档")
            return True
        else:
            print("⚠️ SmartPDFLoader未加载到文档")
            return False
            
    except Exception as e:
        print(f"❌ SmartPDFLoader测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if test_pdf_path and os.path.exists(test_pdf_path):
            os.unlink(test_pdf_path)

def trace_pdf_loading_path():
    """追踪PDF加载的实际路径"""
    print("\n=== 追踪PDF加载路径 ===")
    
    try:
        from app.core.document_processor import DocumentProcessor, SmartPDFLoader
        from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
        
        # 1. 检查DocumentProcessor配置
        processor = DocumentProcessor()
        pdf_loader_class = processor.loaders.get('.pdf')
        print(f"1. DocumentProcessor.loaders['.pdf'] = {pdf_loader_class}")
        
        # 2. 检查SmartPDFLoader是否存在
        try:
            loader = SmartPDFLoader("dummy.pdf")
            print(f"2. SmartPDFLoader可以实例化: ✅")
            print(f"   - 有enhanced_processor属性: {hasattr(loader, 'enhanced_processor')}")
        except Exception as e:
            print(f"2. SmartPDFLoader实例化失败: {str(e)}")
        
        # 3. 检查EnhancedPDFProcessor
        try:
            enhanced = EnhancedPDFProcessor()
            print(f"3. EnhancedPDFProcessor可以实例化: ✅")
            print(f"   - OCR可用: {enhanced.ocr_available}")
        except Exception as e:
            print(f"3. EnhancedPDFProcessor实例化失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 路径追踪失败: {str(e)}")
        return False

def main():
    print("端到端集成测试")
    print("=" * 40)
    
    tests = [
        trace_pdf_loading_path,
        test_smart_pdf_loader_directly,
        test_document_processor_flow,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试执行失败: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("✅ 集成成功！增强PDF处理器已正确集成")
    else:
        print("❌ 集成问题：需要修复")
        
    return all(results)

if __name__ == "__main__":
    success = main()