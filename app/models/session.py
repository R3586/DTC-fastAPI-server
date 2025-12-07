from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"

class SessionPlatform(str, Enum):
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"
    DESKTOP = "desktop"

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    session_token: str  # JTI del refresh token
    refresh_token: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    platform: SessionPlatform = SessionPlatform.WEB
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    location: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    last_active: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )