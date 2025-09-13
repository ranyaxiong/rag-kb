"""
简化的PDF处理功能测试
"""
import sys
import os
sys.path.append('.')

def test_basic_imports():
    """测试基本导入"""
    print("=== 测试基本导入 ===")
    
    try:
        from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
        processor = EnhancedPDFProcessor()
        print("增强PDF处理器: OK")
        print(f"OCR可用: {processor.ocr_available}")
        print(f"图像处理可用: {processor.image_extraction_available}")
        return True
    except Exception as e:
        print(f"增强PDF处理器失败: {str(e)}")
        return False

def test_document_processor():
    """测试文档处理器配置"""
    print("\n=== 测试文档处理器配置 ===")
    
    try:
        from app.core.document_processor import DocumentProcessor, SmartPDFLoader
        processor = DocumentProcessor()
        pdf_loader = processor.loaders.get('.pdf')
        
        if pdf_loader == SmartPDFLoader:
            print("文档处理器配置: OK")
            print("PDF加载器: SmartPDFLoader")
            return True
        else:
            print(f"文档处理器配置: 错误 - 仍在使用 {pdf_loader}")
            return False
    except Exception as e:
        print(f"文档处理器测试失败: {str(e)}")
        return False

def test_pymupdf():
    """测试PyMuPDF"""
    print("\n=== 测试PyMuPDF ===")
    
    try:
        import fitz
        print(f"PyMuPDF版本: {fitz.version}")
        print("PyMuPDF: OK")
        return True
    except Exception as e:
        print(f"PyMuPDF失败: {str(e)}")
        return False

def test_ocr_deps():
    """测试OCR依赖"""
    print("\n=== 测试OCR依赖 ===")
    
    try:
        import pytesseract
        from PIL import Image
        print("pytesseract: OK")
        print("PIL: OK")
        
        # 尝试获取版本
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract版本: {version}")
        except:
            print("Tesseract版本: 无法获取(可能未安装)")
            
        return True
    except ImportError as e:
        print(f"OCR依赖缺失: {str(e)}")
        return False

def main():
    print("PDF处理功能测试")
    print("=" * 30)
    
    tests = [
        test_basic_imports,
        test_document_processor, 
        test_pymupdf,
        test_ocr_deps,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试失败: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 30)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("所有测试通过!")
    else:
        print("部分测试失败")
        
    return all(results)

if __name__ == "__main__":
    success = main()
    print(f"退出码: {0 if success else 1}")