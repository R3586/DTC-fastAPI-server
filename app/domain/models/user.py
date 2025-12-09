from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from bson import ObjectId
from enum import Enum

from app.core.security import PyObjectId


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_thumbnail_url: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    
    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )


class UserCreate(UserBase):
    password: str
    terms_accepted: bool = False
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


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_thumbnail_url: Optional[str] = None
    marketing_emails: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    hashed_password: str
    email_verified: bool = False
    two_factor_enabled: bool = False
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    login_count: int = 0
    storage_used: int = 0  # bytes
    
    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "role": "user",
                "status": "active"
            }
        }
    )


class UserPublic(UserBase):
    id: str
    email_verified: bool
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={ObjectId: str}
    )


class UserProfile(UserPublic):
    """Perfil completo del usuario para mostrar"""
    total_storage_used: int = 0
    total_files: int = 0
    last_active: Optional[datetime] = None