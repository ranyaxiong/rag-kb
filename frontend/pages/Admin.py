import os, requests, streamlit as st
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
st.set_page_config(layout="wide")

def admin_login_form():
    with st.form("admin_login"):
        u = st.text_input("用户名", value="admin")
        p = st.text_input("密码", type="password")
        if st.form_submit_button("登录"):
            r = requests.post(f"{BACKEND}/api/auth/login", data={"username": u, "password": p})
            st.session_state["admin_jwt"] = r.json()["access_token"] if r.ok else None
            st.success("登录成功") if r.ok else st.error("登录失败")


def reset_quota():
    tok = st.session_state.get("admin_jwt")
    if not tok: st.warning("请先登录管理员"); return
    h = {"Authorization": f"Bearer {tok}"}
    r = requests.post(f"{BACKEND}/api/qa/quota/reset", headers=h, timeout=10)
    st.write(r.status_code, r.text)


st.title("管理员控制台")
if "admin_jwt" not in st.session_state:
    admin_login_form()
else:
    st.success("已登录管理员")
    if st.button("重置配额"):
        reset_quota()