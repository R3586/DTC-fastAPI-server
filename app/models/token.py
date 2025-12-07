from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from enum import Enum

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    TWO_FACTOR = "two_factor"

class TokenBlacklist(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    token: str
    token_type: TokenType
    user_id: Optional[str] = None
    expires_at: datetime
    reason: Optional[str] = None
    blacklisted_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )