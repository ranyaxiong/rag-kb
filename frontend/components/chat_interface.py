"""
聊天界面组件
"""
import streamlit as st
import requests
import time


class ChatInterface:
    """聊天界面组件类"""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        
        # 初始化会话状态
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False
    
    def render(self):
        """渲染聊天界面"""
        
        # 聊天历史显示区域
        self._render_chat_history()
        
        # 问题建议
        self._render_suggestions()
        
        # 问题输入区域
        self._render_input_area()
        
        # 清空对话按钮
        if st.session_state.messages and st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.rerun()
    
    def _render_chat_history(self):
        """渲染聊天历史"""
        
        # 聊天容器
        chat_container = st.container()
        
        with chat_container:
            # 显示历史消息
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    
                    # 如果是助手回答，显示来源文档
                    if message["role"] == "assistant" and "sources" in message:
                        self._render_sources(message["sources"])
    
    def _render_sources(self, sources):
        """渲染来源文档"""
        if sources:
            with st.expander("📖 相关文档", expanded=False):
                for i, source in enumerate(sources, 1):
                    st.write(f"**来源 {i}: {source['document_name']}**")
                    st.write(f"相关内容: {source['content']}")
                    if source.get('page_number'):
                        st.write(f"页码: {source['page_number']}")
                    st.markdown("---")
    
    def _render_suggestions(self):
        """渲染问题建议"""
        try:
            response = requests.get(f"{self.backend_url}/api/qa/suggestions", timeout=5)
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get("suggestions", [])
                doc_count = data.get("document_count", 0)
                
                if doc_count == 0:
                    st.info("💡 请先在侧边栏上传一些文档，然后就可以开始提问了！")
                else:
                    st.write("💡 **建议问题:**")
                    cols = st.columns(min(len(suggestions), 3))
                    for i, suggestion in enumerate(suggestions[:3]):
                        with cols[i % 3]:
                            if st.button(suggestion, key=f"suggestion_{i}"):
                                self._process_question(suggestion)
                                
        except Exception as e:
            st.warning("无法获取问题建议")
    
    def _render_input_area(self):
        """渲染输入区域"""
        
        # 问题输入
        user_question = st.chat_input(
            "请输入您的问题...",
            disabled=st.session_state.is_processing
        )
        
        if user_question:
            self._process_question(user_question)
        
        # 高级设置
        with st.expander("⚙️ 高级设置", expanded=False):
            max_sources = st.slider(
                "最大来源文档数量",
                min_value=1,
                max_value=10,
                value=3,
                help="控制回答时参考的文档数量"
            )
            st.session_state.max_sources = max_sources
    
    def _process_question(self, question: str):
        """处理用户问题"""
        
        # 添加用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })
        
        # 显示用户消息
        with st.chat_message("user"):
            st.write(question)
        
        # 设置处理状态
        st.session_state.is_processing = True
        
        # 显示助手思考中
        with st.chat_message("assistant"):
            with st.spinner("正在思考中..."):
                try:
                    # 调用问答API
                    max_sources = getattr(st.session_state, 'max_sources', 3)
                    
                    response = requests.post(
                        f"{self.backend_url}/api/qa/ask",
                        json={
                            "question": question,
                            "max_sources": max_sources
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result.get("answer", "抱歉，我无法回答这个问题。")
                        sources = result.get("sources", [])
                        processing_time = result.get("processing_time", 0)
                        
                        # 显示答案
                        st.write(answer)
                        
                        # 显示处理时间
                        st.caption(f"⏱️ 处理时间: {processing_time:.2f}秒")
                        
                        # 显示来源
                        self._render_sources(sources)
                        
                        # 添加助手消息到历史
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "processing_time": processing_time
                        })
                        
                        # 反馈按钮
                        self._render_feedback(question, answer)
                        
                    else:
                        error_detail = response.json().get("detail", "未知错误")
                        error_msg = f"❌ 处理问题时出错: {error_detail}"
                        st.error(error_msg)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                    
                except requests.exceptions.Timeout:
                    timeout_msg = "❌ 请求超时，请稍后重试"
                    st.error(timeout_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": timeout_msg
                    })
                    
                except Exception as e:
                    error_msg = f"❌ 发生错误: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                finally:
                    # 重置处理状态
                    st.session_state.is_processing = False
        
        # 刷新页面以显示新消息
        st.rerun()
    
    def _render_feedback(self, question: str, answer: str):
        """渲染反馈区域"""
        
        st.write("**这个回答有帮助吗？**")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        feedback_given = False
        
        with col1:
            if st.button("⭐", key=f"feedback_1_{len(st.session_state.messages)}"):
                self._submit_feedback(question, answer, 1)
                feedback_given = True
        
        with col2:
            if st.button("⭐⭐", key=f"feedback_2_{len(st.session_state.messages)}"):
                self._submit_feedback(question, answer, 2)
                feedback_given = True
        
        with col3:
            if st.button("⭐⭐⭐", key=f"feedback_3_{len(st.session_state.messages)}"):
                self._submit_feedback(question, answer, 3)
                feedback_given = True
        
        with col4:
            if st.button("⭐⭐⭐⭐", key=f"feedback_4_{len(st.session_state.messages)}"):
                self._submit_feedback(question, answer, 4)
                feedback_given = True
        
        with col5:
            if st.button("⭐⭐⭐⭐⭐", key=f"feedback_5_{len(st.session_state.messages)}"):
                self._submit_feedback(question, answer, 5)
                feedback_given = True
        
        if feedback_given:
            st.success("感谢您的反馈！")
    
    def _submit_feedback(self, question: str, answer: str, rating: int):
        """提交用户反馈"""
        try:
            requests.post(
                f"{self.backend_url}/api/qa/feedback",
                json={
                    "question": question,
                    "answer": answer,
                    "rating": rating
                },
                timeout=10
            )
        except Exception as e:
            st.error(f"反馈提交失败: {str(e)}")
    
    def get_chat_history(self):
        """获取聊天历史"""
        return st.session_state.messages
    
    def clear_chat_history(self):
        """清空聊天历史"""
        st.session_state.messages = []