# app/models/post_models.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List # Asegúrate de que List esté si lo usas
from datetime import datetime, date # date también si lo usas
from uuid import UUID

class PostBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content_text: str # Hacerlo requerido en Base si siempre se necesita un texto
    social_network: str
    content_type: str
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = 'draft' # Default en Base
    scheduled_at: Optional[datetime] = None # Default en Base

class PostCreate(PostBase):
    # organization_id y author_user_id NO ESTÁN AQUÍ.
    # Se añadirán en el backend antes de la inserción.
    
    # Campos adicionales específicos para la creación si los hubiera,
    # o sobreescrituras de PostBase (ej. si status siempre es 'draft' al crear vía este modelo)
    # status: str = 'draft' # Podrías forzarlo aquí si es diferente al default de PostBase

    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    social_network: Optional[str] = None
    content_type: Optional[str] = None
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    # published_at: Optional[datetime] = None # Usualmente no se actualiza manualmente así
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None


class PostResponse(PostBase):
    id: UUID
    organization_id: UUID # Este SÍ debe estar en la respuesta
    author_user_id: UUID  # Este SÍ debe estar en la respuesta
    
    # Sobreescribir status para que sea mandatorio en la respuesta
    status: str
    
    # Timestamps generados por la DB
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    # Los campos de IA también en la respuesta
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None

    class Config:
        from_attributes = True