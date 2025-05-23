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
    # organization_id: UUID # Considera si esto debe estar en PostBase o solo en Create/Response

class PostCreate(PostBase):
    organization_id: UUID # Asumo que esto es necesario al crear
    # author_user_id se tomará del usuario autenticado, no se envía en el payload
    status: Optional[str] = 'draft'
    scheduled_at: Optional[datetime] = None
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None


class PostUpdate(BaseModel): # Para actualizaciones parciales
    title: Optional[str] = None
    content_text: Optional[str] = None
    social_network: Optional[str] = None
    content_type: Optional[str] = None
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None # Permitir actualizar esto si es necesario
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None
    # No se debería poder cambiar organization_id o author_user_id con un PATCH simple
    # deleted_at se maneja por el endpoint DELETE


class PostResponse(PostBase):
    id: UUID
    organization_id: UUID
    author_user_id: UUID # <<< CAMBIO AQUÍ (antes user_id)
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None


    class Config:
        from_attributes = True # Para Pydantic V2 (reemplaza orm_mode)