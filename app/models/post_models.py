# app/models/post_models.py
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, computed_field
from typing import Optional, List, Dict, Any # Asegúrate que Any esté aquí
from datetime import datetime
from uuid import UUID
from enum import Enum

class ContentTypeEnum(str, Enum):
    IMAGE_POST = "Imagen Única"
    SHORT_TEXT_POST = "Texto Breve"
    CAROUSEL = "Carrusel"
    VERTICAL_VIDEO = "Video Corto"
    INFORMATIVE_VIDEO = "Video Informativo"
    BLOG_ARTICLE = "Artículo"
    TEXT_THREAD = "Hilo de Texto"
    EXTERNAL_LINK = "Publicación con Enlace Externo"
    INTERACTIVE_STORY = "Contenido Efímero Interactivo (Story/Snap)"

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
    content_type: str # <--- CAMBIAR 'str' POR 'ContentTypeEnum'
    media_url: Optional[HttpUrl] = None
    status: Optional[str] = 'draft'
    scheduled_at: Optional[datetime] = None
    model_config = ConfigDict(extra='ignore')

class PostCreate(PostBase):
    prompt_id: Optional[UUID] = None
    generation_group_id: Optional[UUID] = None
    original_post_id: Optional[UUID] = None
    
    # Le añadimos la configuración explícitamente para asegurar la validación correcta
    model_config = ConfigDict(
    )

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
    model_config = ConfigDict(
        extra='forbid',
    )

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
    
    model_config = ConfigDict(from_attributes=True, extra='ignore')