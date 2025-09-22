
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
from utils.realtime_update import setup_realtime_update_system

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
        headers['Authorization'] = f"Bearer {api_key}"
    if provider:
        headers['X-LLM-Provider'] = provider
    if base_url:
        headers['X-LLM-Base-URL'] = base_url
    if model:
        headers['X-LLM-Model'] = model

    return headers

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
    (function(){
      function read(k){
        const v = localStorage.getItem(k);
        try { return JSON.parse(v); } catch(e) { return v || ''; }
      }
      function buildSettings(){
        return {
          api_key: read('rag_byok_api_key') || '',
          provider: read('rag_byok_provider') || 'openai',
          base_url: read('rag_byok_base_url') || '',
          model: read('rag_byok_model') || 'gpt-3.5-turbo'
        };
      }
      function sendOnce(){
        try {
          const settings = buildSettings();
          var el = document.getElementById('settings-data');
          if (el) { el.textContent = JSON.stringify(settings); }
          if (window.parent && window.parent.__rag_listener_installed) {
            window.parent.postMessage({ type:'localStorage_data', data: settings }, '*');
          } else {
            setTimeout(sendOnce, 200);
          }
        } catch(e) {
          setTimeout(sendOnce, 200);
        }
      }
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function(){ setTimeout(sendOnce, 50); });
      } else {
        setTimeout(sendOnce, 50);
      }
    })();
    </script>
    <div id="settings-data" style="display:none;"></div>
    """

    # 显示HTML组件
    st.components.v1.html(html_code, height=0, width=0)

def _normalize_local_storage_value(value: str, default: str = "") -> str:
    """尽可能把localStorage中的值解析为纯文本"""
    if value is None:
        return default

    # localStorage 返回的可能是 JSON 字符串或裸字符串
    cleaned = value
    try:
        cleaned = json.loads(cleaned)
    except Exception:
        pass

    # 早期版本可能出现双重 JSON 编码，这里再尝试一次
    if isinstance(cleaned, str):
        stripped = cleaned.strip()
        if stripped and stripped[0] in ('"', "'") and stripped[-1] == stripped[0]:
            try:
                cleaned = json.loads(cleaned)
            except Exception:
                cleaned = stripped.strip('"')

    if isinstance(cleaned, str):
        return cleaned.strip()

    # 其他类型（如 null/None）统一落到默认值
    return default


def _read_browser_settings() -> dict | None:
    """尝试通过JS一次性读取localStorage中的BYOK设置"""
    if not JS_EVAL_AVAILABLE:
        return None

    try:
        from streamlit_js_eval import streamlit_js_eval

        payload = streamlit_js_eval(
            """
            (function(){
              try {
                const getLS = () => {
                  try { return (window.top && window.top.localStorage) ? window.top.localStorage : localStorage; }
                  catch(e) { return localStorage; }
                };
                const ls = getLS();
                const result = {
                  api_key_raw: ls.getItem('rag_byok_api_key'),
                  provider_raw: ls.getItem('rag_byok_provider'),
                  base_url_raw: ls.getItem('rag_byok_base_url'),
                  model_raw: ls.getItem('rag_byok_model'),
                  last_saved_raw: ls.getItem('rag_byok_last_saved')
                };
                return JSON.stringify(result);
              } catch(e) {
                return '';
              }
            })()
            """,
            key="ls_bulk_read",
            want_output=True
        )
    except Exception as exc:  # pragma: no cover - 针对浏览器端异常
        logger.warning(f"Failed to read BYOK settings via JS eval: {exc}")
        return None

    if not payload or not isinstance(payload, str):
        return None

    try:
        return json.loads(payload)
    except Exception:
        return None


def load_user_settings():
    """从浏览器localStorage加载用户设置"""

    defaults = {
        "byok_api_key": "",
        "byok_provider": "openai",
        "byok_base_url": "",
        "byok_model": "gpt-3.5-turbo"
    }

    # 初始化会话默认值
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    if "settings_loaded" not in st.session_state:
        st.session_state.settings_loaded = False
    if "settings_restoring" not in st.session_state:
        st.session_state.settings_restoring = False
    if "settings_retry_count" not in st.session_state:
        st.session_state.settings_retry_count = 0

    skip_restore = st.session_state.pop('skip_restore_once', False)

    if st.session_state.settings_loaded or skip_restore:
        return

    # 先标记正在恢复，避免提问流程提前启动
    st.session_state.settings_restoring = True

    # 优先尝试通过 URL 参数恢复（兼容历史传参方案）
    try:
        try:
            query_params = dict(st.query_params)
            clear_params = lambda: st.query_params.clear()
        except AttributeError:
            query_params = st.experimental_get_query_params()
            clear_params = lambda: st.experimental_set_query_params()

        restored_flag = query_params.get('restored')
        if restored_flag == '1' or (
            isinstance(restored_flag, list) and restored_flag and restored_flag[0] == '1'
        ):
            import base64

            api_key_param = query_params.get('api_key')
            provider_param = query_params.get('provider', 'openai')
            base_url_param = query_params.get('base_url', '')
            model_param = query_params.get('model', 'gpt-3.5-turbo')

            def _decode_param(value, fallback=""):
                if not value:
                    return fallback
                raw_value = value if isinstance(value, str) else value[0]
                if not raw_value:
                    return fallback
                try:
                    return base64.b64decode(raw_value).decode('utf-8') or fallback
                except Exception:
                    return raw_value or fallback

            api_key = _decode_param(api_key_param)
            provider = provider_param if isinstance(provider_param, str) else provider_param[0]
            base_url = _decode_param(base_url_param)
            model = model_param if isinstance(model_param, str) else model_param[0]

            st.session_state.byok_api_key = api_key.strip()
            st.session_state.byok_provider = (provider or 'openai').strip()
            st.session_state.byok_base_url = base_url.strip()
            st.session_state.byok_model = (model or 'gpt-3.5-turbo').strip()

            st.session_state.settings_loaded = True
            st.session_state.settings_restoring = False
            st.session_state.settings_retry_count = 0

            logger.info(
                "BYOK settings restored from query params: provider=%s, api_key_exists=%s",
                st.session_state.byok_provider,
                bool(api_key)
            )

            clear_params()
            return
    except Exception as exc:
        logger.warning(f"URL param restore failed: {exc}")

    # 通过 JS 直接读取浏览器存储
    raw_data = _read_browser_settings()

    # 如果 JS 读取失败，再尝试 HTML 兜底方式
    if raw_data is None:
        load_with_html_fallback()
        if st.session_state.settings_retry_count < 3:
            st.session_state.settings_retry_count += 1
            st.rerun()
        st.session_state.settings_loaded = True
        st.session_state.settings_restoring = False
        return

    # 解析并规范化各个字段
    api_key = _normalize_local_storage_value(raw_data.get("api_key_raw"))
    provider = _normalize_local_storage_value(raw_data.get("provider_raw"), "openai") or "openai"
    base_url = _normalize_local_storage_value(raw_data.get("base_url_raw"))
    model = _normalize_local_storage_value(raw_data.get("model_raw"), "gpt-3.5-turbo") or "gpt-3.5-turbo"

    st.session_state.byok_api_key = api_key
    st.session_state.byok_provider = provider
    st.session_state.byok_base_url = base_url
    st.session_state.byok_model = model

    st.session_state.settings_loaded = True
    st.session_state.settings_restoring = False
    st.session_state.settings_retry_count = 0

    logger.info(
        "BYOK settings loaded from browser: provider=%s, api_key_exists=%s",
        provider,
        bool(api_key)
    )

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

def main():
    """主应用函数"""

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
                st.session_state.settings_loaded = True
        except Exception as _e:
            logger.info(f"Fallback restore skipped: {type(_e).__name__}: {_e}")

        # Session State 调试（放在 fallback 之后、表单之前，确保展示的就是最新会话值）
        st.code(f"""
                Session State Values:
                - byok_api_key: {bool(st.session_state.get('byok_api_key', ''))}
                - byok_provider: {st.session_state.get('byok_provider', 'N/A')}
                - byok_base_url: {st.session_state.get('byok_base_url', 'N/A')}
                - byok_model: {st.session_state.get('byok_model', 'N/A')}
                - settings_loaded: {st.session_state.get('settings_loaded', False)}
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
- settings_loaded: {st.session_state.get('settings_loaded', False)}
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
        try:
            if st.session_state.get("settings_restoring"):
                st.info("正在从浏览器恢复设置…")
            else:
                # 有自定义Key：直接提示无限制
                if st.session_state.get("byok_api_key"):
                    st.success("🔑 使用自定义 API Key - 不受试用配额限制")
                else:
                    # 无自定义Key：查询后端配额
                    quota_response = requests.get(
                        f"{BACKEND_URL_INTERNAL}/api/qa/quota",
                        headers=build_byok_headers()
                    )
                    if quota_response.status_code == 200:
                        qi = quota_response.json()
                        if not qi.get("quota_enabled", True):
                            st.info("当前未启用配额限制")
                        else:
                            if qi.get("has_custom_key"):
                                st.success("🔑 使用自定义 API Key - 不受试用配额限制")
                            else:
                                used = qi.get("used_count", 0)
                                limit = qi.get("daily_limit", 0)
                                remaining = qi.get("remaining", 0)
                                msg = qi.get("message")
                                st.write(f"今日已用：{used} / 限额：{limit}，剩余：{remaining}")
                                if msg:
                                    st.caption(msg)
                    else:
                        st.info("无法获取配额信息")
        except Exception as e:
            st.warning(f"配额信息获取错误: {str(e)}")

    # 主界面 - 问答系统
    st.header("🤖 智能问答")
    if st.session_state.get("settings_restoring"):
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
