"""
文件上传组件 - 支持实时更新
"""
import streamlit as st
import requests
from typing import List
from utils.state_manager import StateManager, AutoRefreshMixin


class FileUploadComponent(AutoRefreshMixin):
    """文件上传组件类 - 支持实时更新"""

    def __init__(self, backend_url: str, client_url: str = None):
        super().__init__("file_upload", cache_duration=10)  # 10秒缓存
        self.backend_url = backend_url  # 服务器端调用用
        self.client_url = client_url or backend_url  # 浏览器端调用用
        self.supported_formats = [".pdf", ".docx", ".doc", ".txt", ".md"]

        # 初始化状态管理
        StateManager.init_state()

        # 初始化上传状态
        if "uploading" not in st.session_state:
            st.session_state.uploading = False
    
    def _get_max_file_size_mb(self) -> int:
        """从后端获取允许的最大文件大小，失败回退到50MB"""
        try:
            resp = requests.get(f"{self.backend_url}/api/documents/stats/overview", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return int(data.get("storage_info", {}).get("max_file_size_mb", 50))
        except Exception:
            pass
        return 50

    def _calc_upload_timeout(self, size_bytes: int) -> int:
        """根据文件大小动态计算读超时（秒）。更保守：最少180秒，最多1800秒。"""
        try:
            size_mb = max(1, int(size_bytes / (1024 * 1024)))
            # 经验规则：30 秒基数 + 每 MB 5 秒（考虑慢速网络/磁盘写入）
            timeout = 30 + size_mb * 5
            return max(180, min(1800, timeout))
        except Exception:
            return 300
    
    def _check_processing_status(self, document_id: str, filename: str):
        """检查文档处理状态"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/documents/status/{document_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'unknown')
                
                if status == 'completed':
                    st.success(f"✅ {filename} 处理完成!")
                    chunk_count = result.get('chunk_count', 0)
                    if chunk_count > 0:
                        st.info(f"📄 文档已分割成 {chunk_count} 个块，可用于问答")
                elif status == 'failed':
                    err = result.get('error') or result.get('message') or '未知错误'
                    st.error(f"❌ {filename} 处理失败: {err}")
                    # 可选：显示简单建议
                    st.info("💡 建议：确认文档未加密、扫描质量清晰；如为扫描版PDF请稍后重试或压缩体积后再传。")
                elif status == 'processing':
                    progress = result.get('progress')
                    message = result.get('message')
                    if isinstance(progress, int):
                        st.info(f"🔄 {filename} 正在处理中（进度 {progress}%）")
                    else:
                        st.info(f"🔄 {filename} 正在处理中...")
                    if message:
                        st.write(f"📝 {message}")
                    st.info("💡 扫描版PDF处理需要时间，请耐心等待")
                else:
                    st.warning(f"⚠️ {filename} 状态未知: {status}")
            else:
                st.error(f"❌ 无法查询状态: {response.text}")
                
        except Exception as e:
            st.error(f"❌ 查询状态时出错: {str(e)}")
    
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
            upload_disabled = st.session_state.uploading
            if st.button("📤 上传文件", disabled=upload_disabled):
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
            
            upload_disabled = st.session_state.uploading
            if st.button("📤 批量上传", disabled=upload_disabled):
                self._upload_multiple_files(uploaded_files)
    
    def _upload_single_file(self, uploaded_file):
        """上传单个文件"""
        try:
            # 设置上传状态
            st.session_state.uploading = True
            
            # 读取后端限制，超限则提前失败，避免长时间等待
            max_file_size_mb = self._get_max_file_size_mb()
            if uploaded_file.size > max_file_size_mb * 1024 * 1024:
                st.error(f"❌ 文件超过后端限制：{max_file_size_mb} MB。请压缩后重试，或联系管理员提高限制。")
                return

            # 动态计算超时：大文件/扫描PDF需要更长时间传输
            read_timeout = self._calc_upload_timeout(uploaded_file.size)

            with st.spinner(f"正在上传 {uploaded_file.name}..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                
                # 使用异步上传端点，立即返回
                response = requests.post(
                    f"{self.backend_url}/api/documents/upload-async",
                    files=files,
                    timeout=(10, read_timeout)  # (连接超时, 读取超时)
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {uploaded_file.name} 上传成功!")
                    
                    if result.get('processing_mode') == 'async':
                        # 异步处理模式
                        document_id = result.get('document_id')
                        st.info(f"🔄 文档正在后台异步处理中... 文档ID: `{document_id}`")

                        # 添加到处理队列
                        StateManager.add_processing_document(document_id)

                        # 根据文件大小给出更准确的预估时间
                        file_size_mb = uploaded_file.size / (1024 * 1024)
                        if file_size_mb > 10:
                            st.warning("📋 大型文档处理提示：")
                            st.write("• 🔍 扫描版PDF需要OCR文字识别，可能需要3-10分钟")
                            st.write("• 📊 处理进度将实时显示在下方监听区域")
                            st.write("• ✅ 处理完成后会自动更新文档列表和统计信息")
                            st.write("• ⏰ 如果监听超时，请使用右侧刷新按钮查看结果")
                        else:
                            st.info("💡 小型文档通常在1-2分钟内完成处理，完成后会自动更新列表")
                        
                        # 提供状态查询按钮
                        if st.button(f"📊 查看 {uploaded_file.name} 处理状态", key=f"status_{document_id}"):
                            self._check_processing_status(document_id, uploaded_file.name)
                            
                        # 友好提示
                        st.info("💡 **等待期间您可以：**")
                        st.write("• 继续上传其他文档")
                        st.write("• 查看右侧已有文档列表") 
                        st.write("• 测试已有文档的问答功能")
                    else:
                        st.info("文档正在后台处理中，请稍候...")
                    
                    # 显示基本信息
                    if result.get('document_id'):
                        st.code(f"文档ID: {result['document_id']}")
                        document_id = result.get('document_id')
                        if document_id:
                            # 获取用户选择的刷新模式
                            refresh_mode = st.session_state.get('refresh_mode', '手动刷新（默认）')

                            # 使用最终简化的刷新方案
                            from utils.final_refresh import create_simple_auto_refresh_html
                            refresh_html = create_simple_auto_refresh_html(document_id, self.client_url, refresh_mode)
                            st.components.v1.html(refresh_html, height=80)
                    if result.get('filename'):
                        st.code(f"文件名: {result['filename']}")
                elif response.status_code == 409:
                    # 处理重复文件错误
                    error_detail = response.json().get("detail", "文件已存在")
                    st.warning(f"⚠️ {error_detail}")
                else:
                    error_detail = response.json().get("detail", "未知错误")
                    st.error(f"❌ 上传失败: {error_detail}")
                    
        except requests.exceptions.Timeout:
            st.error("❌ 上传超时：文件较大或网络较慢。建议压缩文件、改为批量上传（超时更长），或稍后重试。")
        except Exception as e:
            st.error(f"❌ 上传出错: {str(e)}")
        finally:
            # 重置上传状态
            st.session_state.uploading = False
    
    def _upload_multiple_files(self, uploaded_files: List):
        """批量上传文件"""
        try:
            # 设置上传状态
            st.session_state.uploading = True
            
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
                    timeout=900  # 批量上传增加到15分钟
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
                            if "already exists" in error.lower():
                                st.warning(f"⚠️ {filename}: 文件已存在")
                            else:
                                st.error(f"❌ {filename}: {error}")
                    
                    st.info("所有文件正在后台处理中...")
                    
                else:
                    error_detail = response.json().get("detail", "未知错误")
                    st.error(f"❌ 批量上传失败: {error_detail}")
                    
        except requests.exceptions.Timeout:
            st.error("❌ 批量上传超时，请检查网络连接或稍后重试")
        except Exception as e:
            st.error(f"❌ 批量上传出错: {str(e)}")
        finally:
            # 重置上传状态
            st.session_state.uploading = False
    
    def get_upload_status(self):
        """获取上传状态（预留功能）"""
        # 这里可以实现上传状态检查
        pass
