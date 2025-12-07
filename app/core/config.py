from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache

class Settings(BaseSettings):
    # Aplicación
    APP_NAME: str = "Mi App"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_DAYS_LONG: int = 30
    
    # Cookies
    COOKIE_DOMAIN: Optional[str] = None
    SECURE_COOKIES: bool = True
    SAME_SITE: str = "lax"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Seguridad
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    ACCOUNT_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()