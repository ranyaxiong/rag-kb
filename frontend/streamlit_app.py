"""
Streamlit前端应用
"""
import streamlit as st
import requests
import os
from datetime import datetime
import time

from components.file_upload import FileUploadComponent
from components.chat_interface import ChatInterface

# 配置页面
st.set_page_config(
    page_title="RAG知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置API端点
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def check_backend_connection():
    """检查后端连接"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """主应用函数"""
    
    # 页面标题
    st.title("📚 RAG知识库系统")
    st.markdown("---")
    
    # 检查后端连接
    if not check_backend_connection():
        st.error("⚠️ 后端服务连接失败，请确保API服务正在运行")
        st.info(f"后端地址: {BACKEND_URL}")
        st.stop()
    
    # 侧边栏 - 文档管理
    with st.sidebar:
        st.header("📄 文档管理")
        
        # 文档上传组件
        file_upload_component = FileUploadComponent(BACKEND_URL)
        file_upload_component.render()
        
        st.markdown("---")
        
        # 文档统计
        st.subheader("📊 统计信息")
        try:
            stats_response = requests.get(f"{BACKEND_URL}/api/documents/stats/overview")
            if stats_response.status_code == 200:
                stats = stats_response.json()
                st.metric("总文档数", stats.get("total_documents", 0))
                st.metric("总块数", stats.get("total_chunks", 0))
            else:
                st.error("获取统计信息失败")
        except Exception as e:
            st.error(f"统计信息获取错误: {str(e)}")
    
    # 主界面 - 问答系统
    st.header("🤖 智能问答")
    
    # 聊天界面组件（移出列布局）
    chat_interface = ChatInterface(BACKEND_URL)
    chat_interface.render()
    
    # 右侧栏 - 文档列表
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.empty()  # 占位符
    
    with col2:
        st.header("📋 文档列表")
        
        # 刷新按钮
        if st.button("🔄 刷新文档列表"):
            st.rerun()
        
        # 获取文档列表
        try:
            docs_response = requests.get(f"{BACKEND_URL}/api/documents/")
            if docs_response.status_code == 200:
                documents = docs_response.json()
                
                if documents:
                    for doc in documents:
                        with st.expander(f"📄 {doc['filename']}", expanded=False):
                            st.write(f"**文件类型:** {doc['file_type']}")
                            st.write(f"**状态:** {doc['status']}")
                            st.write(f"**块数量:** {doc.get('chunk_count', 'N/A')}")
                            st.write(f"**上传时间:** {doc['upload_time'][:19]}")
                            
                            # 删除按钮
                            if st.button(f"🗑️ 删除", key=f"delete_{doc['id']}"):
                                delete_response = requests.delete(
                                    f"{BACKEND_URL}/api/documents/{doc['id']}"
                                )
                                if delete_response.status_code == 200:
                                    st.success("文档删除成功!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("文档删除失败")
                else:
                    st.info("暂无上传的文档")
            else:
                st.error("获取文档列表失败")
                
        except Exception as e:
            st.error(f"文档列表获取错误: {str(e)}")


if __name__ == "__main__":
    main()