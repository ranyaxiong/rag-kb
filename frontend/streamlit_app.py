"""
Streamlit前端应用 - 重构版本
使用组件化架构，代码结构更清晰，便于维护
"""
import streamlit as st
import requests
import os
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 导入重构后的组件
from components.model_settings import ModelSettingsComponent
from components.document_manager import DocumentManagerComponent
from components.chat_interface import ChatInterface
from components.document_list import DocumentListComponent
from utils.state_manager import StateManager

# 配置页面
st.set_page_config(
    page_title="RAG知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置API端点
BACKEND_URL_INTERNAL = os.getenv("BACKEND_URL", "http://localhost:8000")  # 服务器端调用
BACKEND_URL_CLIENT = os.getenv("BACKEND_URL_CLIENT", "http://localhost:8000")  # 浏览器端调用


def check_backend_connection() -> bool:
    """检查后端连接"""
    try:
        response = requests.get(f"{BACKEND_URL_INTERNAL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def _setup_auto_refresh_features():
    """设置自动刷新功能"""
    from utils.final_refresh import add_enhanced_refresh_buttons, setup_background_notification, add_refresh_status_indicator
    import datetime

    # 设置后台通知系统
    setup_background_notification()

    # 添加状态指示器
    add_refresh_status_indicator()

    # 添加增强的刷新按钮
    add_enhanced_refresh_buttons()

    # 更新最后刷新时间
    st.session_state.last_refresh_time = datetime.datetime.now().strftime("%H:%M:%S")


def main():
    """主应用函数 - 重构版本，支持实时更新"""

    # 初始化状态管理
    StateManager.init_state()

    # 初始化模型设置组件并加载用户设置
    model_settings = ModelSettingsComponent()
    model_settings.load_user_settings()

    # 页面标题和自动刷新功能
    st.title("📚 RAG知识库系统")

    # 设置自动刷新功能
    _setup_auto_refresh_features()

    st.markdown("---")

    # 检查后端连接
    if not check_backend_connection():
        st.error("⚠️ 后端服务连接失败，请确保API服务正在运行")
        st.info(f"服务器端后端地址: {BACKEND_URL_INTERNAL}")
        st.info(f"浏览器端后端地址: {BACKEND_URL_CLIENT}")
        st.stop()

    # 侧边栏 - 模型与文档管理
    with st.sidebar:
        # 模型设置组件
        model_settings.render()

        st.markdown("---")

        # 自动刷新设置
        from utils.simple_refresh import add_auto_refresh_option
        add_auto_refresh_option()

        st.markdown("---")

        # 文档管理组件（包含统计信息和配额）
        document_manager = DocumentManagerComponent(BACKEND_URL_INTERNAL, BACKEND_URL_CLIENT)
        document_manager.render()

    # 主界面 - 问答系统
    st.header("🤖 智能问答")

    # 检查是否正在恢复设置
    if st.session_state.get("settings_restoring"):
        st.info("正在从浏览器恢复设置…")
        st.stop()

    # 聊天界面组件
    chat_interface = ChatInterface(BACKEND_URL_INTERNAL)
    chat_interface.render()

    # 右侧栏 - 文档列表
    col1, col2 = st.columns([2, 1])

    with col1:
        st.empty()  # 占位符，保持布局

    with col2:
        # 文档列表组件
        document_list = DocumentListComponent(BACKEND_URL_INTERNAL)
        document_list.render()

    # 调试面板（可选）
    with st.expander("🔍 实时更新状态", expanded=False):
        refresh_status = StateManager.get_refresh_status()
        st.json(refresh_status)


if __name__ == "__main__":
    main()