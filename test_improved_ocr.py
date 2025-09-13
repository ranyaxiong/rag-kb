#!/usr/bin/env python3
"""
测试改进后的OCR处理
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_improved_ocr():
    """测试改进的OCR处理"""
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
    
    print(f"测试PDF文件: {os.path.basename(latest_pdf)}")
    
    # 测试改进的增强PDF处理器
    processor = EnhancedPDFProcessor()
    
    try:
        import fitz
        doc = fitz.open(latest_pdf)
        total_pages = len(doc)
        doc.close()
        
        print(f"PDF总页数: {total_pages}")
        print("开始处理（只处理前5页进行测试）...")
        
        # 为了测试，我们创建一个临时的受限处理器
        documents = []
        
        doc = fitz.open(latest_pdf)
        for page_num in range(min(5, total_pages)):
            print(f"\n处理页面 {page_num + 1}...")
            
            page = doc[page_num]
            existing_text = page.get_text().strip()
            
            if len(existing_text) < 50:  # 扫描页面，需要OCR
                # 将页面转换为图像
                import io
                from PIL import Image
                import pytesseract
                
                mat = fitz.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                image = Image.open(io.BytesIO(img_data))
                
                # 预处理图像
                processed_image = processor._preprocess_image_for_ocr(image)
                
                # 使用改进的OCR方法
                ocr_text = processor._perform_ocr_with_fallback(processed_image)
                
                # 清理文本
                cleaned_text = processor._clean_text(ocr_text)
                
                print(f"页面 {page_num + 1} OCR结果长度: {len(cleaned_text)}")
                if cleaned_text.strip():
                    print(f"内容预览: {cleaned_text[:200]}...")
                
                image.close()
                processed_image.close()
                
                if len(cleaned_text.strip()) > 10:
                    from langchain_core.documents import Document
                    document = Document(
                        page_content=cleaned_text,
                        metadata={
                            'source': latest_pdf,
                            'page': page_num + 1,
                            'extraction_method': 'improved_ocr'
                        }
                    )
                    documents.append(document)
        
        doc.close()
        
        print(f"\n测试完成！")
        print(f"成功处理的页面数: {len(documents)}")
        
        total_chars = sum(len(doc.page_content) for doc in documents)
        print(f"总字符数: {total_chars}")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_improved_ocr()