# app/models/post_models.py
from pydantic import BaseModel, Field, HttpUrl, ConfigDict # Importar ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# --- NUEVOS MODELOS PARA GESTIÓN DE IMÁGENES CON CARPETA /wip/ ---

class ConfirmWIPImageDetails(BaseModel):
    path: str = Field(
        ...,
        description="Full storage path (excluding bucket name) of the 'wip' image to confirm. "
                    "Example: {organization_id}/posts/{post_id}/wip/preview_active.png",
        examples=["{organization_id}/posts/{post_id}/wip/preview_active.png"]
    )
    extension: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Extension of the 'wip' image. Example: 'png', 'jpg'.",
        examples=["png"]
    )
    content_type: str = Field( # Añadido según nuestra discusión
        ...,
        description="MIME type of the 'wip' image. Example: 'image/jpeg'.",
        examples=["image/jpeg"]
    )
    model_config = ConfigDict(extra='forbid') # No permitir campos extra

class GeneratePreviewImageRequest(BaseModel):
    custom_prompt: Optional[str] = Field(
        None,
        max_length=4000,
        description="Custom prompt for AI image generation. If None, "
                    "the backend will attempt to generate a prompt from post content."
    )
    model_config = ConfigDict(extra='forbid')

class GeneratePreviewImageResponse(BaseModel):
    preview_image_url: HttpUrl = Field(
        ...,
        description="Public URL of the generated/uploaded preview image in the 'wip' folder (includes cache-busting)."
    )
    preview_storage_path: str = Field(
        ...,
        description="Full storage path (excluding bucket name) of the preview image in the 'wip' folder. "
                    "Example: {organization_id}/posts/{post_id}/wip/preview_active.png"
    )
    preview_image_extension: str = Field(
        ...,
        description="Extension of the generated/uploaded preview image. Example: 'png'."
    )
    preview_content_type: str = Field( # Añadido según nuestra discusión
        ...,
        description="MIME type of the preview image. Example: 'image/png'.",
        examples=["image/png"]
    )
    model_config = ConfigDict(extra='forbid')


# --- MODELOS EXISTENTES (AJUSTADOS PARA PYDANTIC V2) ---

class PostBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content_text: str
    social_network: str
    content_type: str
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = 'draft'
    scheduled_at: Optional[datetime] = None
    model_config = ConfigDict(extra='ignore') # Ignorar campos extra si vienen de la DB

class PostCreate(PostBase):
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None
    # model_config = ConfigDict(from_attributes=True) # Si es para input, no se necesita from_attributes
    # from_attributes es para cuando creas el modelo desde un objeto ORM
    # Para PostCreate que es un payload de request, no se necesita a menos que lo construyas de otra forma.
    # Lo mismo para PostUpdate

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content_text: Optional[str] = None
    social_network: Optional[str] = None
    content_type: Optional[str] = None
    
    media_url: Optional[HttpUrl] = Field(None, description="URL pública de la nueva imagen principal, o null para borrar la actual.")
    media_storage_path: Optional[str] = Field(None, description="Ruta de almacenamiento (sin bucket) de la nueva imagen principal, o null para borrar la actual.")
    
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None

    confirm_wip_image_details: Optional[ConfirmWIPImageDetails] = Field(
        None,
        description="Detalles para confirmar una imagen de la carpeta 'wip' como la imagen principal del post."
    )
    model_config = ConfigDict(extra='forbid') # Para payloads de request, 'forbid' es bueno

class PostResponse(PostBase):
    id: UUID
    organization_id: UUID
    author_user_id: UUID
    status: str
    media_storage_path: Optional[str] = Field(None, description="Ruta de almacenamiento (sin bucket) de la imagen principal, si existe.")
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True, extra='ignore') # Para respuestas desde la DB, from_attributes es clave