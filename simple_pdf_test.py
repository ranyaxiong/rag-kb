#!/usr/bin/env python3
"""
简化的PDF测试，专注于诊断扫描版PDF处理问题
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_pdf_processing():
    """测试PDF处理"""
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
    print(f"文件大小: {os.path.getsize(latest_pdf)} 字节")
    
    # 测试增强PDF处理器
    processor = EnhancedPDFProcessor()
    print(f"OCR可用: {processor.ocr_available}")
    
    try:
        # 只处理前3页来快速诊断问题
        documents = []
        
        import fitz  # PyMuPDF
        doc = fitz.open(latest_pdf)
        print(f"PDF总页数: {len(doc)}")
        
        # 分析前3页
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            print(f"\n--- 页面 {page_num + 1} ---")
            
            # 获取现有文本
            existing_text = page.get_text()
            print(f"现有文本长度: {len(existing_text)}")
            if existing_text.strip():
                print(f"现有文本预览: {existing_text[:100]}...")
            
            # 获取图像信息
            image_list = page.get_images()
            print(f"图像数量: {len(image_list)}")
            
            # 如果是扫描页面，尝试OCR
            if len(existing_text.strip()) < 50 and len(image_list) > 0:
                print("尝试OCR处理...")
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # 将页面转换为图像
                    mat = fitz.Matrix(1.5, 1.5)  # 较低分辨率用于测试
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # 使用PIL打开图像
                    image = Image.open(io.BytesIO(img_data))
                    
                    # 简单的英文OCR测试
                    ocr_text = pytesseract.image_to_string(image, lang='eng')
                    print(f"OCR文本长度: {len(ocr_text)}")
                    if ocr_text.strip():
                        print(f"OCR文本预览: {ocr_text[:100]}...")
                    
                    image.close()
                    
                except Exception as e:
                    print(f"OCR处理失败: {str(e)}")
        
        doc.close()
        
    except Exception as e:
        print(f"处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_processing()