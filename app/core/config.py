from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

load_dotenv()
class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str
    
    # Server
    HOST: str
    PORT: int
    WORKERS: int
    
    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    MONGODB_MAX_POOL_SIZE: int
    MONGODB_MIN_POOL_SIZE: int
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    REFRESH_TOKEN_EXPIRE_DAYS_LONG: int
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] 
    
    # Storage - S3/MinIO
    STORAGE_PROVIDER: str 
    STORAGE_ENDPOINT: Optional[str] 
    STORAGE_ACCESS_KEY: str 
    STORAGE_SECRET_KEY: str 
    STORAGE_REGION: str 
    STORAGE_BUCKET: str 
    STORAGE_SECURE: bool 
    STORAGE_PUBLIC_URL: Optional[str] 
    
    # MinIO specific (for development)
    MINIO_ENDPOINT: str 
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool 
    
    # Image Processing
    AVATAR_MAX_SIZE_MB: int 
    AVATAR_ALLOWED_TYPES: List[str]
    AVATAR_MAX_WIDTH: int
    AVATAR_MAX_HEIGHT: int
    AVATAR_THUMBNAIL_SIZE: int
    
    model_config = SettingsConfigDict(
        env_file=".env",  # Todavía podemos dejar esto como referencia
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignora campos extra en el .env
        env_prefix="",  # Sin prefijo para las variables
    )

@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()