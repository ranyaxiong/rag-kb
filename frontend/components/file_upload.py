"""
文件上传组件
"""
import streamlit as st
import requests
from typing import List


class FileUploadComponent:
    """文件上传组件类"""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.supported_formats = [".pdf", ".docx", ".doc", ".txt", ".md"]
    
    def render(self):
        """渲染文件上传界面"""
        
        st.subheader("📤 上传文档")
        
        # 显示支持的格式
        with st.expander("支持的文件格式", expanded=False):
            for fmt in self.supported_formats:
                st.write(f"• {fmt}")
        
        # 单文件上传
        st.write("**单文件上传:**")
        uploaded_file = st.file_uploader(
            "选择文件",
            type=["pdf", "docx", "doc", "txt", "md"],
            help="支持PDF、Word、文本和Markdown文件"
        )
        
        if uploaded_file is not None:
            # 显示文件信息
            st.write(f"**文件名:** {uploaded_file.name}")
            st.write(f"**文件大小:** {uploaded_file.size / 1024:.2f} KB")
            
            # 上传按钮
            if st.button("📤 上传文件"):
                self._upload_single_file(uploaded_file)
        
        st.markdown("---")
        
        # 批量上传
        st.write("**批量上传:**")
        uploaded_files = st.file_uploader(
            "选择多个文件",
            type=["pdf", "docx", "doc", "txt", "md"],
            accept_multiple_files=True,
            help="可以同时选择多个文件进行批量上传"
        )
        
        if uploaded_files:
            st.write(f"已选择 {len(uploaded_files)} 个文件:")
            for file in uploaded_files:
                st.write(f"• {file.name}")
            
            if st.button("📤 批量上传"):
                self._upload_multiple_files(uploaded_files)
    
    def _upload_single_file(self, uploaded_file):
        """上传单个文件"""
        try:
            with st.spinner(f"正在上传 {uploaded_file.name}..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                
                response = requests.post(
                    f"{self.backend_url}/api/documents/upload",
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {uploaded_file.name} 上传成功!")
                    st.info("文档正在后台处理中，请稍候...")
                    
                    # 显示文档信息
                    doc_info = result.get("document", {})
                    if doc_info:
                        st.json(doc_info)
                        
                else:
                    error_detail = response.json().get("detail", "未知错误")
                    st.error(f"❌ 上传失败: {error_detail}")
                    
        except requests.exceptions.Timeout:
            st.error("❌ 上传超时，请检查网络连接或稍后重试")
        except Exception as e:
            st.error(f"❌ 上传出错: {str(e)}")
    
    def _upload_multiple_files(self, uploaded_files: List):
        """批量上传文件"""
        try:
            with st.spinner(f"正在批量上传 {len(uploaded_files)} 个文件..."):
                
                # 准备文件数据
                files = []
                for uploaded_file in uploaded_files:
                    files.append(
                        ("files", (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type))
                    )
                
                response = requests.post(
                    f"{self.backend_url}/api/documents/batch-upload",
                    files=files,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ 批量上传完成!")
                    
                    # 显示每个文件的结果
                    results = result.get("results", [])
                    for file_result in results:
                        filename = file_result.get("filename", "未知文件")
                        if file_result.get("success"):
                            st.success(f"✅ {filename}: 上传成功")
                        else:
                            error = file_result.get("error", "未知错误")
                            st.error(f"❌ {filename}: {error}")
                    
                    st.info("所有文件正在后台处理中...")
                    
                else:
                    error_detail = response.json().get("detail", "未知错误")
                    st.error(f"❌ 批量上传失败: {error_detail}")
                    
        except requests.exceptions.Timeout:
            st.error("❌ 批量上传超时，请检查网络连接或稍后重试")
        except Exception as e:
            st.error(f"❌ 批量上传出错: {str(e)}")
    
    def get_upload_status(self):
        """获取上传状态（预留功能）"""
        # 这里可以实现上传状态检查
        pass