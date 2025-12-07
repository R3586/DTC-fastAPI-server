from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    device_id: Optional[str] = None
    device_name: Optional[str] = None

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: Optional[str] = None
    terms_accepted: bool
    marketing_emails: bool = False
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "Str0ngP@ssword123",
                "full_name": "John Doe",
                "terms_accepted": True
            }
        }
    )

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    logout_all: bool = False

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v