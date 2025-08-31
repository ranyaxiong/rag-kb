"""
配置管理模块
"""
import os
import json
import base64
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基本配置
    app_name: str = "RAG Knowledge Base"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # LLM配置 - 支持多种模型提供商
    llm_provider: str = "openai"  # 支持: openai, deepseek, zhipu, etc.
    embedding_provider: str = "openai"  # 嵌入模型提供商，可以与LLM提供商不同
    
    # API配置 - 支持多种获取方式
    api_key: Optional[str] = None
    api_key_file: Optional[str] = None
    api_key_base64: Optional[str] = None
    
    # 智谱AI配置
    zhipu_api_key: Optional[str] = None
    
    # 向后兼容的OpenAI配置
    openai_api_key: Optional[str] = None
    openai_api_key_file: Optional[str] = None
    openai_api_key_base64: Optional[str] = None
    
    # 模型配置
    api_base_url: Optional[str] = None  # 自定义API端点
    embedding_api_base_url: Optional[str] = None  # 嵌入模型API端点
    chat_model: str = "gpt-3.5-turbo"  # 聊天模型
    embedding_model: str = "text-embedding-ada-002"  # 嵌入模型
    
    # 存储配置
    upload_dir: str = "./data/uploads"
    chroma_db_path: str = "./data/chroma_db"
    
    # 服务器配置
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_host: str = "0.0.0.0"
    frontend_port: int = 8501
    
    # RAG配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_sources: int = 3
    similarity_threshold: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.chroma_db_path, exist_ok=True)
    
    def get_api_key(self) -> Optional[str]:
        """安全地获取API Key（支持多种提供商）"""
        # 方式1: 新的通用API key配置
        if self.api_key:
            return self.api_key
        
        # 方式2: 从文件读取
        if self.api_key_file:
            try:
                with open(self.api_key_file, 'r') as f:
                    key = f.read().strip()
                    if key:
                        logger.info(f"API key loaded from file: {self.api_key_file}")
                        return key
            except Exception as e:
                logger.warning(f"Failed to read API key from file {self.api_key_file}: {e}")
        
        # 方式3: 从base64编码的环境变量
        if self.api_key_base64:
            try:
                key = base64.b64decode(self.api_key_base64).decode('utf-8').strip()
                if key:
                    logger.info("API key loaded from base64 environment variable")
                    return key
            except Exception as e:
                logger.warning(f"Failed to decode base64 API key: {e}")
        
        # 向后兼容：方式4: 检查OpenAI特定配置
        if self.openai_api_key:
            return self.openai_api_key
        
        if self.openai_api_key_file:
            try:
                with open(self.openai_api_key_file, 'r') as f:
                    key = f.read().strip()
                    if key:
                        logger.info(f"API key loaded from OpenAI file: {self.openai_api_key_file}")
                        return key
            except Exception as e:
                logger.warning(f"Failed to read OpenAI API key from file: {e}")
        
        if self.openai_api_key_base64:
            try:
                key = base64.b64decode(self.openai_api_key_base64).decode('utf-8').strip()
                if key:
                    logger.info("API key loaded from OpenAI base64 environment variable")
                    return key
            except Exception as e:
                logger.warning(f"Failed to decode OpenAI base64 API key: {e}")
        
        # 方式5: 从Docker secrets
        secret_name = f"{self.llm_provider}_api_key" if self.llm_provider != "openai" else "openai_api_key"
        docker_secret_path = f"/run/secrets/{secret_name}"
        if os.path.exists(docker_secret_path):
            try:
                with open(docker_secret_path, 'r') as f:
                    key = f.read().strip()
                    if key:
                        logger.info(f"API key loaded from Docker secret: {secret_name}")
                        return key
            except Exception as e:
                logger.warning(f"Failed to read Docker secret {secret_name}: {e}")
        
        # 方式6: 从系统密钥环 (仅Linux/Mac)
        try:
            import keyring
            key = keyring.get_password("rag-kb", f"{self.llm_provider}_api_key")
            if not key and self.llm_provider != "openai":
                # 回退到openai密钥环配置
                key = keyring.get_password("rag-kb", "openai_api_key")
            if key:
                logger.info(f"API key loaded from system keyring for {self.llm_provider}")
                return key
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to get API key from keyring: {e}")
        
        logger.warning(f"No valid API key found for {self.llm_provider} in any source")
        return None
    
    def get_openai_api_key(self) -> Optional[str]:
        """向后兼容：获取OpenAI API Key"""
        return self.get_api_key()
    
    def get_embedding_api_key(self) -> Optional[str]:
        """获取嵌入模型的API Key"""
        if self.embedding_provider == "zhipu":
            return self.zhipu_api_key
        else:
            return self.get_api_key()
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取当前模型配置"""
        config = {
            "provider": self.llm_provider,
            "embedding_provider": self.embedding_provider,
            "chat_model": self.chat_model,
            "embedding_model": self.embedding_model,
            "api_base_url": self.api_base_url,
            "embedding_api_base_url": self.embedding_api_base_url
        }
        
        # 根据不同提供商设置默认值
        if self.llm_provider == "deepseek":
            config.setdefault("api_base_url", "https://api.deepseek.com")
            if self.chat_model == "gpt-3.5-turbo":  # 如果还是默认值
                config["chat_model"] = "deepseek-chat"
        elif self.llm_provider == "zhipu":
            config.setdefault("api_base_url", "https://open.bigmodel.cn/api/paas/v4")
            if self.chat_model == "gpt-3.5-turbo":
                config["chat_model"] = "glm-4"
        elif self.llm_provider == "openai":
            config.setdefault("api_base_url", "https://api.openai.com/v1")
        
        # 嵌入模型配置
        if self.embedding_provider == "zhipu":
            if not config["embedding_api_base_url"]:
                config["embedding_api_base_url"] = "https://open.bigmodel.cn/api/paas/v4"
            if self.embedding_model == "text-embedding-ada-002":
                config["embedding_model"] = "embedding-3"
        elif self.embedding_provider == "openai":
            if not config["embedding_api_base_url"]:
                config["embedding_api_base_url"] = "https://api.openai.com/v1"
        
        return config


# 全局配置实例
settings = Settings()