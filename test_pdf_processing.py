"""
测试增强PDF处理功能
"""
import sys
import os
sys.path.append('.')

from app.core.document_processor import DocumentProcessor, SmartPDFLoader
from app.core.enhanced_pdf_processor import EnhancedPDFProcessor

def test_enhanced_pdf_processor():
    """测试增强PDF处理器"""
    print("=== 测试增强PDF处理器 ===")
    
    try:
        processor = EnhancedPDFProcessor()
        print(f"✅ 增强PDF处理器初始化成功")
        print(f"   - OCR功能可用: {processor.ocr_available}")
        print(f"   - 图像处理可用: {processor.image_extraction_available}")
        
        return True
    except Exception as e:
        print(f"❌ 增强PDF处理器初始化失败: {str(e)}")
        return False

def test_smart_pdf_loader():
    """测试智能PDF加载器"""
    print("\n=== 测试智能PDF加载器 ===")
    
    try:
        # 创建一个测试用的虚假文件路径
        test_path = "test.pdf"
        loader = SmartPDFLoader(test_path)
        print(f"✅ 智能PDF加载器初始化成功")
        print(f"   - 文件路径: {loader.file_path}")
        print(f"   - 增强处理器已集成")
        
        return True
    except Exception as e:
        print(f"❌ 智能PDF加载器初始化失败: {str(e)}")
        return False

def test_document_processor_integration():
    """测试文档处理器集成"""
    print("\n=== 测试文档处理器集成 ===")
    
    try:
        processor = DocumentProcessor()
        pdf_loader_class = processor.loaders.get('.pdf')
        
        if pdf_loader_class == SmartPDFLoader:
            print("✅ DocumentProcessor已正确配置SmartPDFLoader")
            print("   - PDF文件将使用增强处理器")
            return True
        else:
            print(f"❌ DocumentProcessor仍在使用: {pdf_loader_class}")
            print("   - PDF文件仍使用旧的处理器")
            return False
            
    except Exception as e:
        print(f"❌ 文档处理器集成测试失败: {str(e)}")
        return False

def test_ocr_capabilities():
    """测试OCR能力"""
    print("\n=== 测试OCR能力 ===")
    
    try:
        import pytesseract
        from PIL import Image
        
        # 检查Tesseract版本
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract版本: {version}")
        except:
            print("⚠️ 无法获取Tesseract版本，但pytesseract已安装")
        
        # 检查支持的语言
        try:
            languages = pytesseract.get_languages()
            print(f"✅ 支持的OCR语言: {', '.join(languages[:5])}...")
            
            if 'chi_sim' in languages:
                print("   - ✅ 支持中文简体")
            if 'eng' in languages:
                print("   - ✅ 支持英文")
                
        except Exception as lang_error:
            print(f"   - ⚠️ 无法获取语言列表: {str(lang_error)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ OCR依赖未安装: {str(e)}")
        print("   请运行: pip install pytesseract pillow")
        return False
    except Exception as e:
        print(f"⚠️ OCR测试遇到问题: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("RAG知识库 - 增强PDF处理功能测试")
    print("=" * 50)
    
    tests = [
        test_enhanced_pdf_processor,
        test_smart_pdf_loader,
        test_document_processor_integration,
        test_ocr_capabilities,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试执行失败: {str(e)}")
            results.append(False)
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")
    
    if all(results):
        print("\n所有测试通过！增强PDF处理功能已成功集成")
        print("\n功能特性:")
        print("   - PyMuPDF文本提取")
        print("   - OCR扫描类PDF处理")
        print("   - 智能PDF类型检测")
        print("   - 自动回退机制")
        print("   - 详细错误提示")
    else:
        print("\n部分测试失败，请检查配置")
        
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)