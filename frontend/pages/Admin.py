import os, requests, streamlit as st
from datetime import datetime, timedelta
import jwt

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
st.set_page_config(
    page_title="管理员控制台",
    page_icon="🔐",
    layout="wide"
)
st.sidebar.write(f"Backend URL: {BACKEND}")


def check_token_validity():
    """检查JWT令牌是否有效"""
    token = st.session_state.get("admin_jwt")
    if not token:
        return False
    
    try:
        # 不验证签名，只检查过期时间
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get('exp')
        if exp:
            exp_time = datetime.fromtimestamp(exp)
            if datetime.now() > exp_time:
                return False
        return True
    except:
        return False

def admin_login_form():
    """管理员登录表单"""
    st.title("🔐 管理员登录")
    st.markdown("---")
    
    with st.form("admin_login"):
        u = st.text_input("用户名", value="admin", placeholder="请输入管理员用户名")
        p = st.text_input("密码", type="password", placeholder="请输入密码")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("🔓 登录", use_container_width=True, type="primary")
        with col2:
            if st.form_submit_button("← 返回主页", use_container_width=True):
                st.switch_page("streamlit_app.py")
        
        if submit:
            if not u or not p:
                st.error("❌ 请填写用户名和密码")
                return
                
            try:
                r = requests.post(
                    f"{BACKEND}/api/auth/login", 
                    data={"username": u, "password": p},
                    timeout=10
                )
                st.write(f"状态码: {r.status_code}")
                st.write(f"响应头: {r.headers}")
                st.write(f"响应内容: {r.text[:500]}")  # 显示前500个字符
                if r.ok:
                    token_data = r.json()
                    st.session_state["admin_jwt"] = token_data["access_token"]
                    st.success("✅ 登录成功！正在跳转...")
                    st.rerun()
                else:
                    error_detail = r.json().get("detail", "未知错误")
                    st.error(f"❌ 登录失败: {error_detail}")
            except requests.exceptions.Timeout:
                st.error("❌ 请求超时，请检查后端服务")
            except requests.exceptions.ConnectionError:
                st.error("❌ 无法连接到后端服务")
            except Exception as e:
                st.error(f"❌ 登录失败: {str(e)}")

def reset_quota():
    """重置用户配额"""
    tok = st.session_state.get("admin_jwt")
    if not tok:
        st.warning("⚠️ 请先登录管理员")
        return
    
    try:
        h = {"Authorization": f"Bearer {tok}"}
        r = requests.post(f"{BACKEND}/api/qa/quota/reset", headers=h, timeout=10)
        
        if r.status_code == 200:
            result = r.json()
            if result.get("success"):
                st.success(f"✅ {result.get('message', '配额重置成功')}")
            else:
                st.warning(f"⚠️ {result.get('message', '配额重置失败')}")
        elif r.status_code == 403:
            st.error("❌ 权限不足，令牌可能已过期，请重新登录")
            del st.session_state["admin_jwt"]
            st.rerun()
        else:
            st.error(f"❌ 操作失败 (HTTP {r.status_code}): {r.text}")
    except Exception as e:
        st.error(f"❌ 请求失败: {str(e)}")

def get_quota_stats():
    """获取配额统计"""
    tok = st.session_state.get("admin_jwt")
    if not tok:
        st.warning("⚠️ 请先登录管理员")
        return
    
    try:
        h = {"Authorization": f"Bearer {tok}"}
        r = requests.get(f"{BACKEND}/api/qa/quota/stats", headers=h, timeout=10)
        
        if r.status_code == 200:
            stats = r.json()
            st.json(stats)
        elif r.status_code == 403:
            st.error("❌ 权限不足，令牌可能已过期，请重新登录")
            del st.session_state["admin_jwt"]
            st.rerun()
        else:
            st.error(f"❌ 获取失败 (HTTP {r.status_code})")
    except Exception as e:
        st.error(f"❌ 请求失败: {str(e)}")

def admin_panel():
    """管理员控制面板"""
    st.title("📊 管理员控制台")
    
    # 顶部状态栏
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.success("✅ 管理员已登录")
    with col2:
        if st.button("🏠 返回主页", use_container_width=True):
            st.switch_page("streamlit_app.py")
    with col3:
        if st.button("🚪 退出登录", use_container_width=True):
            del st.session_state["admin_jwt"]
            st.success("已退出登录")
            st.rerun()
    
    st.markdown("---")
    
    # 功能选项卡
    tab1, tab2, tab3 = st.tabs(["📊 配额管理", "📈 系统统计", "⚙️ 系统设置"])
    
    with tab1:
        st.subheader("配额管理")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 重置用户配额")
            st.info("重置当前用户的查询配额（基于IP和User-Agent）")
            if st.button("🔄 重置配额", type="primary", use_container_width=True):
                reset_quota()
        
        with col_b:
            st.markdown("#### 配额统计")
            st.info("查看所有用户的配额使用情况")
            if st.button("📊 查看统计", use_container_width=True):
                get_quota_stats()
    
    with tab2:
        st.subheader("系统统计")
        
        try:
            response = requests.get(f"{BACKEND}/api/documents/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📄 总文档数", stats.get("document_count", 0))
                with col2:
                    st.metric("🔢 向量数", stats.get("vector_count", 0))
                with col3:
                    storage_mb = stats.get("storage_mb", 0)
                    st.metric("💾 存储空间", f"{storage_mb:.2f} MB")
                with col4:
                    st.metric("📦 集合数", stats.get("collection_count", 1))
                
                st.markdown("---")
                st.json(stats)
            else:
                st.error("无法获取系统统计")
        except Exception as e:
            st.error(f"获取统计失败: {str(e)}")
    
    with tab3:
        st.subheader("系统设置")
        st.info("🚧 系统设置功能开发中...")
        st.markdown("""
        **计划功能：**
        - ⚙️ 修改配额限制
        - 👥 用户管理
        - 🔑 API密钥管理
        - 📝 系统日志查看
        - 🔄 缓存清理
        """)

# 主逻辑
if not st.session_state.get("admin_jwt") or not check_token_validity():
    if st.session_state.get("admin_jwt"):
        # 令牌已过期
        st.warning("⚠️ 登录已过期，请重新登录")
        del st.session_state["admin_jwt"]
    admin_login_form()
else:
    admin_panel()
