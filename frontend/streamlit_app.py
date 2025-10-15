
"""
Streamlit前端应用
"""
import streamlit as st
import requests
import os
from datetime import datetime
import time
import json
import logging
import uuid
import subprocess

logger = logging.getLogger(__name__)

def get_git_version_info_frontend():
    """在Streamlit前端获取git版本信息"""
    try:
        # 在应用的根目录执行git命令
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=project_root
        ).strip().decode('utf-8')
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=project_root
        ).strip().decode('utf-8')[:7]
        return f"v: {branch} ({commit})"
    except Exception:
        return "v: unknown"

def detect_provider_from_api_key(api_key: str) -> str:
    """根据API Key格式自动检测提供商"""
    if not api_key:
        return "openai"

    api_key = api_key.strip()

    # Zhipu API keys have the format: xxxxxxxx.xxxxxxxxxxxxxx (32 char hex + . + 16 chars)
    # Check this first since it has a unique format
    if "." in api_key and len(api_key.split(".")) == 2:
        parts = api_key.split(".")
        if len(parts[0]) == 32 and len(parts[1]) == 16:
            return "zhipu"

    # OpenAI API keys start with "sk-" and are longer (51-55 chars typically)
    if api_key.startswith("sk-") and len(api_key) >= 48:
        return "openai"

    # DeepSeek API keys start with "sk-" and are shorter than OpenAI keys
    if api_key.startswith("sk-") and len(api_key) <= 47:
        return "deepseek"

    # Default to openai if pattern doesn't match
    return "openai"

# 尝试导入streamlit-js-eval，如果没有则使用备用方案
try:
    from streamlit_js_eval import streamlit_js_eval, get_geolocation
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False
    st.warning("⚠️ 建议安装 streamlit-js-eval 以获得更好的设置持久化体验: pip install streamlit-js-eval")

from components.file_upload import FileUploadComponent
from components.chat_interface import ChatInterface

from utils.state_manager import StateManager
from utils.settings_loader import load_user_settings as load_user_settings_shared, SettingsStatus
from utils.realtime_update import setup_realtime_update_system

# 配置页面
st.set_page_config(
    page_title="RAG知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


def add_floating_admin_button():
    """添加右上角浮动的管理员登录按钮"""
    is_logged_in = st.session_state.get("admin_jwt") is not None
    
    # 根据登录状态决定按钮样式和文本
    if is_logged_in:
        bg_color = "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)"
        button_text = "✓ 管理员"
        tooltip_text = "进入管理面板"
    else:
        bg_color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        button_text = "🔐"
        tooltip_text = "管理员登录"
    
    button_html = f"""
    <style>
    /* 浮动按钮主体 */
    .floating-admin-btn {{
        position: fixed;
        top: 70px;
        right: 20px;
        z-index: 999999;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: {bg_color};
        box-shadow: 0 4px 12px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-decoration: none;
        font-size: 24px;
        border: 2px solid rgba(255,255,255,0.3);
    }}
    
    /* 悬停效果 */
    .floating-admin-btn:hover {{
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 8px 20px rgba(0,0,0,0.25), 0 4px 8px rgba(0,0,0,0.15);
    }}
    
    /* 点击效果 */
    .floating-admin-btn:active {{
        transform: translateY(-1px) scale(0.98);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}
    
    /* 提示文本 */
    .admin-tooltip {{
        position: fixed;
        top: 80px;
        right: 85px;
        background: rgba(38, 39, 48, 0.95);
        color: white;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease, transform 0.25s ease;
        z-index: 999998;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transform: translateX(10px);
    }}
    
    /* 提示文本箭头 */
    .admin-tooltip::after {{
        content: '';
        position: absolute;
        right: -6px;
        top: 50%;
        transform: translateY(-50%);
        border-left: 6px solid rgba(38, 39, 48, 0.95);
        border-top: 6px solid transparent;
        border-bottom: 6px solid transparent;
    }}
    
    /* 悬停时显示提示 */
    .floating-admin-btn:hover + .admin-tooltip {{
        opacity: 1;
        transform: translateX(0);
    }}
    
    /* 登录状态指示器（小绿点） */
    .status-indicator {{
        position: absolute;
        top: 4px;
        right: 4px;
        width: 12px;
        height: 12px;
        background: #4CAF50;
        border-radius: 50%;
        border: 2px solid white;
        animation: pulse 2s infinite;
        display: {'block' if is_logged_in else 'none'};
    }}
    
    @keyframes pulse {{
        0%, 100% {{
            transform: scale(1);
            opacity: 1;
        }}
        50% {{
            transform: scale(1.1);
            opacity: 0.8;
        }}
    }}
    
    /* 响应式设计 */
    @media (max-width: 768px) {{
        .floating-admin-btn {{
            width: 48px;
            height: 48px;
            top: 60px;
            right: 15px;
            font-size: 20px;
        }}
        .admin-tooltip {{
            font-size: 12px;
            padding: 6px 10px;
        }}
    }}
    </style>
    
    <a href="/_Admin" target="_self" class="floating-admin-btn" title="{tooltip_text}">
        {button_text}
        <span class="status-indicator"></span>
    </a>
    <div class="admin-tooltip">{tooltip_text}</div>
    """
    
    st.markdown(button_html, unsafe_allow_html=True)


# 配置API端点
# Docker环境中，前端容器使用backend服务名，但浏览器需要使用localhost
BACKEND_URL_INTERNAL = os.getenv("BACKEND_URL", "http://localhost:8000")  # 服务器端调用
BACKEND_URL_CLIENT = os.getenv("BACKEND_URL_CLIENT", "http://localhost:8000")  # 浏览器端调用

# 初始化前端实时更新系统（用于无刷新更新统计与文档列表）
setup_realtime_update_system(BACKEND_URL_CLIENT)


def init_websocket_connection(client_id: str):
    """使用JS注入WebSocket连接"""
    ws_url = f"{BACKEND_URL_CLIENT.replace('http', 'ws')}/ws/{client_id}"

    js_code = f"""
    <script>
    (function() {{
        if (!window.ragWs) {{
            console.log('Attempting to connect WebSocket to {ws_url}');
            const ws = new WebSocket('{ws_url}');
            ws.onopen = () => console.log('WebSocket connection established.');
            ws.onclose = () => console.log('WebSocket connection closed.');
            ws.onerror = (error) => console.error('WebSocket error:', error);
            window.ragWs = ws;
        }}
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)


def build_byok_headers() -> dict:
    """根据当前会话中的 BYOK 设置构造请求头"""
    headers = {}
    api_key = st.session_state.get('byok_api_key', '').strip()
    provider = st.session_state.get('byok_provider', '').strip()
    base_url = st.session_state.get('byok_base_url', '').strip()
    model = st.session_state.get('byok_model', '').strip()

    if api_key:
        headers['LLM-Api-Key'] = api_key
    if provider:
        headers['LLM-Provider'] = provider
    if base_url:
        headers['LLM-Base-URL'] = base_url
    if model:
        headers['LLM-Model'] = model

    return headers

def check_backend_connection():
    """检查后端连接"""
    try:
        response = requests.get(f"{BACKEND_URL_INTERNAL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def load_with_html_fallback():
    """Deprecated: use utils.settings_loader._load_with_html_fallback via shared loader."""
    pass

def _normalize_local_storage_value(value: str, default: str = "") -> str:
    """Deprecated: normalization is handled in utils.settings_loader."""
    return value if isinstance(value, str) else default


def _read_browser_settings() -> dict | None:
    """Deprecated: reading handled in utils.settings_loader."""
    return None


def load_user_settings():
    """统一入口：使用共享加载器实现设置恢复与重试。"""
    load_user_settings_shared()

def save_user_settings():
    """保存用户设置到浏览器localStorage"""
    api_key = st.session_state.get('byok_api_key', '')
    provider = st.session_state.get('byok_provider', 'openai')
    base_url = st.session_state.get('byok_base_url', '')
    model = st.session_state.get('byok_model', 'gpt-3.5-turbo')

    timestamp = datetime.utcnow().isoformat()

    js_template = """
    localStorage.setItem('rag_byok_api_key', {api_key});
    localStorage.setItem('rag_byok_provider', {provider});
    localStorage.setItem('rag_byok_base_url', {base_url});
    localStorage.setItem('rag_byok_model', {model});
    localStorage.setItem('rag_byok_last_saved', {timestamp});
    """

    js_expr = js_template.format(
        api_key=json.dumps(api_key),
        provider=json.dumps(provider),
        base_url=json.dumps(base_url),
        model=json.dumps(model),
        timestamp=json.dumps(timestamp)
    )

    if JS_EVAL_AVAILABLE:
        try:
            streamlit_js_eval(
                js_expressions=js_expr,
                key="save_ls_byok",
                want_output=False
            )
            logger.info("BYOK settings saved via JS eval: provider=%s, api_key_exists=%s", provider, bool(api_key))
            return
        except Exception as exc:
            logger.warning(f"JS-eval save failed, fallback to HTML: {exc}")

    st.components.v1.html(
        f"""
        <script>
        (function() {{
            try {{
                {js_expr}
            }} catch (e) {{
                console.error('Failed to save BYOK settings:', e);
            }}
        }})();
        </script>
        """,
        height=0,
        width=0
    )
    logger.info("BYOK settings saved via HTML fallback: provider=%s, api_key_exists=%s", provider, bool(api_key))


def clear_user_settings():
    """清除用户设置（覆盖 top 与当前上下文的 localStorage）"""
    if JS_EVAL_AVAILABLE:
        try:
            import time
            from streamlit_js_eval import streamlit_js_eval
            js_code = """
            (function(){
              try{
                const getLS = () => { try { return (window.top && window.top.localStorage) ? window.top.localStorage : localStorage; } catch(e) { return localStorage; } };
                const ls = getLS();
                ['rag_byok_api_key','rag_byok_provider','rag_byok_base_url','rag_byok_model','rag_byok_last_saved'].forEach(k=>{ try{ ls.removeItem(k); }catch(_){} });
                ['rag_byok_api_key','rag_byok_provider','rag_byok_base_url','rag_byok_model','rag_byok_last_saved'].forEach(k=>{ try{ localStorage.removeItem(k); }catch(_){} });
                console.log('All BYOK settings cleared');
              }catch(e){ console.error('clear error', e); }
            })();
            """
            streamlit_js_eval(
                js_expressions=js_code,
                key=f"clear_all_settings_{int(time.time()*1000)}",
                want_output=False
            )
        except Exception as e:
            logger.warning(f"清除设置时出错: {e}")
    else:
        clear_js = """
        <script>
        (function(){
          try{
            ['rag_byok_api_key','rag_byok_provider','rag_byok_base_url','rag_byok_model','rag_byok_last_saved'].forEach(k=>{ try{ localStorage.removeItem(k); }catch(_){} });
            if (window.top && window.top!==window && window.top.localStorage){
              ['rag_byok_api_key','rag_byok_provider','rag_byok_base_url','rag_byok_model','rag_byok_last_saved'].forEach(k=>{ try{ window.top.localStorage.removeItem(k); }catch(_){} });
            }
            console.log('BYOK settings cleared (fallback)');
          }catch(e){ console.error('fallback clear error', e); }
        })();
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
                    last_saved: localStorage.getItem('rag_byok_last_saved'),
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


def display_quota_info():
    try:
        if st.session_state.get("settings_status") == SettingsStatus.RESTORING.value:
            st.info("正在从浏览器恢复设置…")
            return

        if st.session_state.get("byok_api_key"):
            st.success("🔑 使用自定义 API Key - 不受试用配额限制")
            return

        response = requests.get(
            f"{BACKEND_URL_INTERNAL}/api/qa/quota",
            headers=build_byok_headers()
        )

        if response.status_code != 200:
            st.info("无法获取配额信息")
            return

        quota_info = response.json()

        if not quota_info.get("quota_enabled", True):
            st.info("当前未启用配额限制")
            return

        used = quota_info.get("used_count", 0)
        limit = quota_info.get("daily_limit", 0)
        remaining = quota_info.get("remaining", 0)
        message = quota_info.get("message")

        st.write(f"今日已用：{used} / 限额：{limit}，剩余：{remaining}")
        if message:
            st.caption(message)

    except Exception as e:
        st.warning(f"配额信息获取错误: {str(e)}")


def main():
    """主应用函数"""
    
    # 添加右上角浮动管理员按钮
    add_floating_admin_button()

    # --- WebSocket & Client ID Management ---
    if 'client_id' not in st.session_state:
        st.session_state.client_id = str(uuid.uuid4())
        # Place a container at the top to initialize WS
        with st.container():
             init_websocket_connection(st.session_state.client_id)

    # 在页面启动时检查是否需要重置保存标志
    # 使用一个简单的机制：如果用户刷新浏览器，session_state会清空
    # 所以我们不需要手动重置settings_just_saved

    # 加载用户设置
    load_user_settings()

    # 页面标题
    st.title("📚 RAG知识库系")
    st.markdown("---")

    # 检查后端连接
    if not check_backend_connection():
        st.error("⚠️ 后端服务连接失败，请确保API服务正在运行")
        st.info(f"服务器端后端地址: {BACKEND_URL_INTERNAL}")
        st.info(f"浏览器端后端地址: {BACKEND_URL_CLIENT}")
        st.stop()
    # --- Plan A: 原生轮询 + 智能降频（有任务时短周期自动重跑）---
    try:
        StateManager.init_state()
        processing_docs = list(StateManager.get_processing_documents())
        if processing_docs:
            # 轮询每个进行中的文档状态，完成即从列表移除
            finished_ids: list[str] = []
            for _doc_id in list(processing_docs):
                try:
                    resp = requests.get(
                        f"{BACKEND_URL_INTERNAL}/api/documents/status/{_doc_id}", timeout=4
                    )
                    if resp.status_code == 200:
                        status = (resp.json() or {}).get("status")
                        if status in ("completed", "failed", "timeout"):
                            StateManager.remove_processing_document(_doc_id)
                            finished_ids.append(_doc_id)
                except Exception:
                    # 网络错误时忽略，下一轮再查
                    pass

            remaining = len(StateManager.get_processing_documents())
            # 只要还有任务或刚有任务完成，就触发一次短周期自动刷新
            if remaining > 0 or finished_ids:
                st.caption(f"🔄 正在处理 {remaining} 个文档… 页面将自动更新。")
                time.sleep(2)  # 轻量降频：2s/次
                st.rerun()
    except Exception:
        pass


    # 侧边栏 - 模型与文档管理
    with st.sidebar:
        # 在侧边栏顶部显示版本信息
        st.caption(get_git_version_info_frontend())

        st.header("🔑 模型设置 (BYOK)")

        # 总是显示调试信息来排查问题
        st.write("**调试信息：**")
        # localStorage调试
        st.caption(f"JS Eval available: {JS_EVAL_AVAILABLE}")
        debug_info = debug_localStorage()
        st.code(debug_info, language="json")

        # Fallback: 如果 load_user_settings 首次未能取到值，这里用调试读取到的 localStorage 结果再补写一次
        try:
            _parsed = json.loads(debug_info) if isinstance(debug_info, str) else {}
            def _unquote(v, default=""):
                if v is None:
                    return default
                try:
                    return (json.loads(v) if isinstance(v, str) else v) or default
                except Exception:
                    return v or default
            # 仅当当前会话没有key，且本轮不是“跳过恢复/刚清除”时，才进行兜底恢复
            if (not st.session_state.get('byok_api_key')) and (not st.session_state.get('skip_restore_once')) and (not st.session_state.get('just_cleared')):
                st.session_state.byok_api_key = (_unquote(_parsed.get('api_key'), "")).strip()
                st.session_state.byok_provider = (_unquote(_parsed.get('provider'), 'openai')).strip()
                st.session_state.byok_base_url = (_unquote(_parsed.get('base_url'), "")).strip()
                st.session_state.byok_model = (_unquote(_parsed.get('model'), 'gpt-3.5-turbo')).strip()
                st.session_state.settings_status = SettingsStatus.LOADED.value
        except Exception as _e:
            logger.info(f"Fallback restore skipped: {type(_e).__name__}: {_e}")

        # Session State 调试（放在 fallback 之后、表单之前，确保展示的就是最新会话值）
        st.code(f"""
                Session State Values:
                - byok_api_key: {bool(st.session_state.get('byok_api_key', ''))}
                - byok_provider: {st.session_state.get('byok_provider', 'N/A')}
                - byok_base_url: {st.session_state.get('byok_base_url', 'N/A')}
                - byok_model: {st.session_state.get('byok_model', 'N/A')}
                - settings_status: {st.session_state.get('settings_status', 'idle')}
                - settings_attempts: {st.session_state.get('settings_attempts', 0)}
                - settings_just_saved: {st.session_state.get('settings_just_saved', False)}
        """)

        with st.form("byok_form"):
            api_key = st.text_input("API Key", type="password", value=st.session_state.byok_api_key, help="设置将保存在浏览器本地，刷新页面不会丢失")

            # Auto-detect provider based on API key format
            detected_provider = detect_provider_from_api_key(api_key) if api_key else st.session_state.byok_provider
            provider_options = ["openai", "deepseek", "zhipu", "custom"]
            current_provider = st.session_state.byok_provider

            # Show detected provider hint
            if api_key and detected_provider != current_provider:

                st.info(f"💡 检测到 API Key 格式，建议选择提供商: **{detected_provider}**")

            provider = st.selectbox("提供商", options=provider_options, index=provider_options.index(current_provider))
            base_url = st.text_input("Base URL (可选)", value=st.session_state.byok_base_url, placeholder="如自定义兼容 OpenAI 的网关地址")
            model = st.text_input("模型 (可选)", value=st.session_state.byok_model, placeholder="如 gpt-4o-mini / deepseek-chat / glm-4")

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                saved = st.form_submit_button("💾 保存设置", on_click=lambda: st.session_state.__setitem__('skip_restore_once', True))
            with col2:
                auto_detect = st.form_submit_button("🎯 自动检测", on_click=lambda: st.session_state.__setitem__('skip_restore_once', True))
            with col3:
                cleared = st.form_submit_button("🗑️ 清除设置", on_click=lambda: st.session_state.__setitem__('skip_restore_once', True))

            if auto_detect and api_key:
                # Auto-detect and apply provider settings
                detected = detect_provider_from_api_key(api_key)
                st.session_state.byok_api_key = api_key.strip()
                st.session_state.byok_provider = detected
                # Set appropriate defaults based on provider
                if detected == "deepseek":
                    st.session_state.byok_base_url = "https://api.deepseek.com"
                    st.session_state.byok_model = "deepseek-chat"
                elif detected == "zhipu":
                    st.session_state.byok_base_url = "https://open.bigmodel.cn/api/paas/v4"
                    st.session_state.byok_model = "glm-4"
                elif detected == "openai":
                    st.session_state.byok_base_url = ""
                    st.session_state.byok_model = "gpt-3.5-turbo"

                save_user_settings()
                # 标记设置已保存，不需要重新加载
                st.session_state.settings_just_saved = True
                st.success(f"✅ 已自动检测并配置为 {detected} 提供商")
                st.rerun()

            if saved:
                # 更新session_state
                st.session_state.byok_api_key = api_key.strip()
                st.session_state.byok_provider = provider.strip()
                st.session_state.byok_base_url = base_url.strip()
                st.session_state.byok_model = model.strip()

                # 保存到localStorage
                save_user_settings()
                # 标记设置已保存，不需要重新加载
                st.session_state.settings_just_saved = True
                st.success("✅ 设置已保存到浏览器本地，刷新页面不会丢失")


            if cleared:

                # 清除session_state
                st.session_state.byok_api_key = ""
                st.session_state.byok_provider = "openai"
                st.session_state.byok_base_url = ""
                st.session_state.byok_model = "gpt-3.5-turbo"

                # 清除localStorage
                clear_user_settings()
                # 标记设置已清除，使用当前session_state的默认值，并避免本轮/下一轮恢复
                st.session_state.settings_just_saved = True
                st.session_state.just_cleared = True
                st.success("🗑️ 设置已清除")

        st.markdown("---")

        st.header("📄 文档管理")

        # 文档上传组件
        file_upload_component = FileUploadComponent(
            BACKEND_URL_INTERNAL,
            BACKEND_URL_CLIENT
        )
        file_upload_component.render()

        st.markdown("---")

        # Session State
        st.code(f"""
Session State Values (after form):
- byok_api_key: {bool(st.session_state.get('byok_api_key', ''))}
- byok_provider: {st.session_state.get('byok_provider', 'N/A')}
- byok_base_url: {st.session_state.get('byok_base_url', 'N/A')}
- byok_model: {st.session_state.get('byok_model', 'N/A')}
- settings_status: {st.session_state.get('settings_status', 'idle')}
- settings_attempts: {st.session_state.get('settings_attempts', 0)}
- settings_just_saved: {st.session_state.get('settings_just_saved', False)}
        """)

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
        display_quota_info()

        

    # 主界面 - 问答系统
    st.header("🤖 智能问答")
    if st.session_state.get("settings_status") == SettingsStatus.RESTORING.value:
        st.info("正在从浏览器恢复设置…")
        st.stop()

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
