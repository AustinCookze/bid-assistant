from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    # API Keys
    MOONSHOT_API_KEY: str = "sk-8YvWRliaCJrcVBLvfQgopi0ebEiwEcKyTdVbYajiiKYmHmCZ"
    
    # 模型配置 - 支持的可选模型：moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k, kimi-k2.5
    MODEL_NAME: str = "moonshot-v1-128k"  # 使用 Moonshot 128k 上下文模型
    MODEL_BASE_URL: str = "https://api.moonshot.cn/v1"
    
    # 应用配置
    APP_NAME: str = "招投标助手 v1.1"
    DEBUG: bool = False
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
