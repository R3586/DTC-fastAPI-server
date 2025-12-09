from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class FileUploadRequest(BaseModel):
    """Schema para subida de archivos"""
    public: bool = False
    tags: Optional[list[str]] = None


class FileUploadResponse(BaseModel):
    """Respuesta de subida de archivo"""
    id: str
    filename: str
    original_name: str
    content_type: str
    size: int
    path: str
    url: str
    bucket: str
    public: bool
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AvatarUploadResponse(BaseModel):
    """Respuesta específica para avatar"""
    avatar_url: str
    avatar_thumbnail_url: str
    message: str = "Avatar uploaded successfully"