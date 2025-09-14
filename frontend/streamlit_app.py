"""
Streamlit前端应用
"""
import streamlit as st
import requests
import os
from datetime import datetime
import time
import json

# 尝试导入streamlit-js-eval，如果没有则使用备用方案
try:
    from streamlit_js_eval import streamlit_js_eval, get_geolocation
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False
    st.warning("⚠️ 建议安装 streamlit-js-eval 以获得更好的设置持久化体验: pip install streamlit-js-eval")

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
# Docker环境中，前端容器使用backend服务名，但浏览器需要使用localhost
BACKEND_URL_INTERNAL = os.getenv("BACKEND_URL", "http://localhost:8000")  # 服务器端调用
BACKEND_URL_CLIENT = os.getenv("BACKEND_URL_CLIENT", "http://localhost:8000")  # 浏览器端调用

def check_backend_connection():
    """检查后端连接"""
    try:
        response = requests.get(f"{BACKEND_URL_INTERNAL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def load_with_html_fallback():
    """使用HTML方式读取localStorage的备用方案"""
    # 创建一个隐藏的HTML组件来读取localStorage
    html_code = """
    <script>
    // 读取localStorage并设置到隐藏元素中
    function loadSettings() {
        const settings = {
            api_key: localStorage.getItem('rag_byok_api_key') || '',
            provider: localStorage.getItem('rag_byok_provider') || 'openai',
            base_url: localStorage.getItem('rag_byok_base_url') || '',
            model: localStorage.getItem('rag_byok_model') || 'gpt-3.5-turbo'
        };

        // 将设置数据发送给父窗口
        window.parent.postMessage({
            type: 'localStorage_data',
            data: settings
        }, '*');

        // 也设置到隐藏元素中作为备用
        document.getElementById('settings-data').textContent = JSON.stringify(settings);
    }

    // 页面加载完成后执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadSettings);
    } else {
        loadSettings();
    }
    </script>
    <div id="settings-data" style="display:none;"></div>
    """

    # 显示HTML组件
    st.components.v1.html(html_code, height=0, width=0)

def load_user_settings():
    """从浏览器localStorage加载用户设置"""
    # 初始化默认设置
    defaults = {
        "byok_api_key": "",
        "byok_provider": "openai",
        "byok_base_url": "",
        "byok_model": "gpt-3.5-turbo"
    }

    # 从session_state或默认值初始化
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # 尝试从localStorage加载设置（注意：组件首次渲染返回None，需要等待下一次重渲染）
    if not st.session_state.get("settings_loaded", False):
        if JS_EVAL_AVAILABLE:
            try:
                api_key = streamlit_js_eval(
                    js_expressions="localStorage.getItem('rag_byok_api_key')",
                    key="load_api_key",
                    want_output=True,
                )
                provider = streamlit_js_eval(
                    js_expressions="localStorage.getItem('rag_byok_provider')",
                    key="load_provider",
                    want_output=True,
                )
                base_url = streamlit_js_eval(
                    js_expressions="localStorage.getItem('rag_byok_base_url')",
                    key="load_base_url",
                    want_output=True,
                )
                model = streamlit_js_eval(
                    js_expressions="localStorage.getItem('rag_byok_model')",
                    key="load_model",
                    want_output=True,
                )

                # 只有在组件返回了有效值（非None）时才应用并标记为已加载
                got_any_value = any(v is not None for v in [api_key, provider, base_url, model])
                if got_any_value:
                    if isinstance(api_key, str) and api_key.strip():
                        st.session_state.byok_api_key = api_key.strip()
                    if isinstance(provider, str) and provider.strip():
                        st.session_state.byok_provider = provider.strip()
                    if isinstance(base_url, str) and base_url.strip():
                        st.session_state.byok_base_url = base_url.strip()
                    if isinstance(model, str) and model.strip():
                        st.session_state.byok_model = model.strip()
                    st.session_state["settings_loaded"] = True
            except Exception as e:
                st.warning(f"从localStorage加载设置时出错: {e}")
        else:
            # 无JS组件时不做强制标记，保持每次渲染尝试
            pass


def save_user_settings():
    """保存用户设置到浏览器localStorage"""
    if JS_EVAL_AVAILABLE:
        # 使用streamlit-js-eval保存到localStorage
        try:
            # 获取当前设置值
            api_key = st.session_state.get('byok_api_key', '')
            provider = st.session_state.get('byok_provider', 'openai')
            base_url = st.session_state.get('byok_base_url', '')
            model = st.session_state.get('byok_model', 'gpt-3.5-turbo')

            # 保存到localStorage，使用want_output=False因为我们不需要返回值
            streamlit_js_eval(
                js_expressions=f"localStorage.setItem('rag_byok_api_key', {json.dumps(api_key)})",
                key="save_api_key",
                want_output=False
            )
            streamlit_js_eval(
                js_expressions=f"localStorage.setItem('rag_byok_provider', {json.dumps(provider)})",
                key="save_provider",
                want_output=False
            )
            streamlit_js_eval(
                js_expressions=f"localStorage.setItem('rag_byok_base_url', {json.dumps(base_url)})",
                key="save_base_url",
                want_output=False
            )
            streamlit_js_eval(
                js_expressions=f"localStorage.setItem('rag_byok_model', {json.dumps(model)})",
                key="save_model",
                want_output=False
            )

            # 验证保存是否成功
            streamlit_js_eval(
                js_expressions="console.log('Settings saved to localStorage:', localStorage.getItem('rag_byok_api_key'))",
                key="verify_save",
                want_output=False
            )

        except Exception as e:
            st.error(f"保存设置时出错: {e}")
    else:
        # 备用方案：使用原有的HTML方法
        api_key = st.session_state.get('byok_api_key', '')
        provider = st.session_state.get('byok_provider', 'openai')
        base_url = st.session_state.get('byok_base_url', '')
        model = st.session_state.get('byok_model', 'gpt-3.5-turbo')

        js_code = f"""
        <script>
        // 保存设置到localStorage
        localStorage.setItem('rag_byok_api_key', {json.dumps(api_key)});
        localStorage.setItem('rag_byok_provider', {json.dumps(provider)});
        localStorage.setItem('rag_byok_base_url', {json.dumps(base_url)});
        localStorage.setItem('rag_byok_model', {json.dumps(model)});
        console.log('Settings saved to localStorage via HTML fallback');
        console.log('API Key saved:', localStorage.getItem('rag_byok_api_key'));
        </script>
        """

        st.components.v1.html(js_code, height=0, width=0)


def clear_user_settings():
    """清除用户设置"""
    if JS_EVAL_AVAILABLE:
        try:
            streamlit_js_eval(js_expressions="localStorage.removeItem('rag_byok_api_key')", key="clear_api_key")
            streamlit_js_eval(js_expressions="localStorage.removeItem('rag_byok_provider')", key="clear_provider")
            streamlit_js_eval(js_expressions="localStorage.removeItem('rag_byok_base_url')", key="clear_base_url")
            streamlit_js_eval(js_expressions="localStorage.removeItem('rag_byok_model')", key="clear_model")
        except Exception as e:
            st.error(f"清除设置时出错: {e}")
    else:
        # 备用方案
        clear_js = """
        <script>
        localStorage.removeItem('rag_byok_api_key');
        localStorage.removeItem('rag_byok_provider');
        localStorage.removeItem('rag_byok_base_url');
        localStorage.removeItem('rag_byok_model');
        console.log('Settings cleared from localStorage');
        </script>
        """
        st.components.v1.html(clear_js, height=0, width=0)

def debug_localStorage():
    """调试localStorage状态"""
    if JS_EVAL_AVAILABLE:
        try:
            # 读取所有localStorage值进行调试
            debug_info = streamlit_js_eval(
                js_expressions="""
                JSON.stringify({
                    api_key: localStorage.getItem('rag_byok_api_key'),
                    provider: localStorage.getItem('rag_byok_provider'),
                    base_url: localStorage.getItem('rag_byok_base_url'),
                    model: localStorage.getItem('rag_byok_model'),
                    all_keys: Object.keys(localStorage).filter(k => k.startsWith('rag_'))
                })
                """,
                key="debug_localStorage",
                want_output=True
            )
            return debug_info
        except Exception as e:
            return f"调试localStorage时出错: {e}"
    else:
        return "streamlit-js-eval 不可用"

def main():
    """主应用函数"""
    
    # 加载用户设置
    load_user_settings()
    
    # 页面标题
    st.title("📚 RAG知识库系统")
    st.markdown("---")
    
    # 检查后端连接
    if not check_backend_connection():
        st.error("⚠️ 后端服务连接失败，请确保API服务正在运行")
        st.info(f"服务器端后端地址: {BACKEND_URL_INTERNAL}")
        st.info(f"浏览器端后端地址: {BACKEND_URL_CLIENT}")
        st.stop()
    
    # 侧边栏 - 模型与文档管理
    with st.sidebar:
        st.header("🔑 模型设置 (BYOK)")
        
        with st.form("byok_form"):
            api_key = st.text_input("API Key", type="password", value=st.session_state.byok_api_key, help="设置将保存在浏览器本地，刷新页面不会丢失")
            provider = st.selectbox("提供商", options=["openai", "deepseek", "zhipu", "custom"], index=["openai","deepseek","zhipu","custom"].index(st.session_state.byok_provider))
            base_url = st.text_input("Base URL (可选)", value=st.session_state.byok_base_url, placeholder="如自定义兼容 OpenAI 的网关地址")
            model = st.text_input("模型 (可选)", value=st.session_state.byok_model, placeholder="如 gpt-4o-mini / deepseek-chat / glm-4")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                saved = st.form_submit_button("💾 保存设置")
            with col2:
                cleared = st.form_submit_button("🗑️ 清除设置")
            
            if saved:
                # 更新session_state
                st.session_state.byok_api_key = api_key.strip()
                st.session_state.byok_provider = provider.strip()
                st.session_state.byok_base_url = base_url.strip()
                st.session_state.byok_model = model.strip()
                
                # 保存到localStorage
                save_user_settings()
                st.success("✅ 设置已保存到浏览器本地，刷新页面不会丢失")

                # 显示调试信息
                if st.checkbox("🔍 显示localStorage调试信息", key="debug_checkbox"):
                    debug_info = debug_localStorage()
                    st.code(debug_info, language="json")
                
            if cleared:
                # 清除session_state
                st.session_state.byok_api_key = ""
                st.session_state.byok_provider = "openai"
                st.session_state.byok_base_url = ""
                st.session_state.byok_model = "gpt-3.5-turbo"
                
                # 清除localStorage
                clear_user_settings()
                st.success("🗑️ 设置已清除")
                st.rerun()

        st.markdown("---")

        st.header("📄 文档管理")
        
        # 文档上传组件
        file_upload_component = FileUploadComponent(BACKEND_URL_INTERNAL)
        file_upload_component.render()
        
        st.markdown("---")
        
        # 文档统计
        st.subheader("📊 统计信息")
        try:
            stats_response = requests.get(f"{BACKEND_URL_INTERNAL}/api/documents/stats/overview")
            if stats_response.status_code == 200:
                stats = stats_response.json()
                st.metric("总文档数", stats.get("total_documents", 0))
                st.metric("总块数", stats.get("total_chunks", 0))
            else:
                st.error("获取统计信息失败")
        except Exception as e:
            st.error(f"统计信息获取错误: {str(e)}")
        
        # 配额信息显示
        st.subheader("📊 使用配额")
        try:
            # 构建请求头（如果用户设置了BYOK）
            headers = {}
            if st.session_state.get("byok_api_key"):
                headers["Authorization"] = f"Bearer {st.session_state.byok_api_key}"
                if st.session_state.get("byok_provider"):
                    headers["X-LLM-Provider"] = st.session_state.byok_provider
                if st.session_state.get("byok_base_url"):
                    headers["X-LLM-Base-URL"] = st.session_state.byok_base_url
                if st.session_state.get("byok_model"):
                    headers["X-LLM-Model"] = st.session_state.byok_model
            
            quota_response = requests.get(f"{BACKEND_URL_INTERNAL}/api/qa/quota", headers=headers)
            if quota_response.status_code == 200:
                quota_info = quota_response.json()
                
                if not quota_info.get("quota_enabled"):
                    st.info("🔓 配额限制已禁用")
                elif quota_info.get("has_custom_key"):
                    st.success("🔑 使用自定义API Key - 无限制")
                else:
                    # 显示配额信息
                    used = quota_info.get("used_count", 0)
                    daily_limit = quota_info.get("daily_limit", 5)
                    remaining = quota_info.get("remaining", 0)
                    
                    # 配额进度条
                    progress = used / daily_limit if daily_limit > 0 else 0
                    st.metric("今日已用", f"{used}/{daily_limit}")
                    st.metric("剩余次数", remaining)
                    
                    # 进度条颜色根据使用情况变化
                    if remaining == 0:
                        st.error("⚠️ 配额已用完")
                        st.info("💡 填写上方API Key可无限制使用")
                    elif remaining <= 1:
                        st.warning(f"⏰ 仅剩 {remaining} 次提问")
                        st.progress(progress)
                    else:
                        st.success(f"✅ 还可提问 {remaining} 次")
                        st.progress(progress)
            else:
                st.warning("获取配额信息失败")
        except Exception as e:
            st.warning(f"配额信息获取错误: {str(e)}")
    
    # 主界面 - 问答系统
    st.header("🤖 智能问答")
    
    # 聊天界面组件（移出列布局）
    chat_interface = ChatInterface(BACKEND_URL_INTERNAL)
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
            docs_response = requests.get(f"{BACKEND_URL_INTERNAL}/api/documents/")
            if docs_response.status_code == 200:
                documents = docs_response.json()
                
                if documents:
                    for doc in documents:
                        with st.expander(f"📄 {doc['filename']}", expanded=False):
                            st.write(f"**文件类型:** {doc['file_type']}")
                            st.write(f"**状态:** {doc['status']}")
                            st.write(f"**块数量:** {doc.get('chunk_count', 'N/A')}")
                            st.write(f"**上传时间:** {doc['upload_time'][:19]}")
                            
                            # 一键聚焦此文档进行问答（设置检索范围）
                            if st.button("🎯 基于此文档提问", key=f"focus_{doc['id']}"):
                                st.session_state.selected_doc_id = doc['id']
                                st.success("已限定检索范围到该文档。回到上方聊天区继续提问。")
                                time.sleep(1)
                                st.rerun()
                            
                            # 删除按钮
                            if st.button(f"🗑️ 删除", key=f"delete_{doc['id']}"):
                                delete_response = requests.delete(
                                    f"{BACKEND_URL_INTERNAL}/api/documents/{doc['id']}"
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