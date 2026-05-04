from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "car-showroom-api"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    INTERNAL_SERVICE_TOKEN: str
    
    UPLOAD_DIR: str = "./uploads"
    BASE_URL: str = "http://localhost:8000"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
