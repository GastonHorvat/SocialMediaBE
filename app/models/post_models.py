# app/models/post_models.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

class PostBase(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    social_network: str
    content_type: str
    media_url: Optional[HttpUrl] = None

class PostCreate(PostBase):
    status: Optional[str] = 'draft'
    scheduled_at: Optional[datetime] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    social_network: Optional[str] = None
    content_type: Optional[str] = None
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    # No es común actualizar deleted_at directamente aquí, se maneja por el endpoint DELETE

class PostResponse(PostBase):
    id: UUID
    user_id: UUID
    status: str
    scheduled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None # <<< AÑADE ESTA LÍNEA

    # (Opcional) prompt_id: Optional[UUID] = None
    # ...

    class Config:
        from_attributes = True # Para Pydantic V2