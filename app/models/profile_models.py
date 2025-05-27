# app/models/profile_models.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, title="Nombre Completo", max_length=255)
    avatar_url: Optional[str] = Field(None, title="URL del Avatar", max_length=1024) # URL puede ser larga
    timezone: Optional[str] = Field(None, title="Zona Horaria", max_length=50)
    # No incluimos campos de notificación aquí, podrían ir en otro modelo/endpoint si son muchos

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    id: UUID # El user_id
    email: Optional[EmailStr] = None # El email de auth.users
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC" # Default si no está en DB (aunque tu DB ya tiene default)
    # Podrías añadir los campos de notificación si los quieres en esta respuesta también
    # notify_post_published_email: bool = True 
    # ... etc ...
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True