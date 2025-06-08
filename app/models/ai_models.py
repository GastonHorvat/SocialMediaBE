# app/models/ai_models.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict
from uuid import UUID 


# -------------------------------------------------------------------------------------------------------------
# Modelos para la Generación de IDEAS Y TITULOS DE CONTENIDO
# -------------------------------------------------------------------------------------------------------------

class GeneratedIdeaDetail(BaseModel):
    """Representa una única idea de contenido generada por la IA, con sus componentes."""
    hook: Optional[str] = Field(None, description="Frase de gancho o titular corto para la idea.")
    content_description: Optional[str] = Field(None, alias="description", description="Descripción concisa del concepto del post.") # El alias 'description' ayuda si el LLM usa esa clave
    suggested_format: Optional[str] = Field(None, description="Formato de contenido sugerido para la idea.")

    class Config:
        from_attributes = True  # Para Pydantic v2 (o orm_mode = True para v1)
        populate_by_name = True # Permite que el alias "description" funcione al validar desde un dict


class ContentIdeasResponse(BaseModel):
    """Respuesta del endpoint que devuelve una lista de ideas de contenido detalladas."""
    ideas: List[GeneratedIdeaDetail]

    class Config:
        from_attributes = True

# --- NUEVOS MODELOS PARA GENERACIÓN DE TÍTULOS ---

class GenerateTitlesFromFullIdeaRequest(BaseModel):
    """Petición para generar títulos basados en el texto completo de una idea de contenido."""
    full_content_idea_text: str = Field(
        ..., # Mandatorio
        min_length=20,
        description="El texto completo de la idea de contenido (puede incluir el hook, la descripción y el formato sugerido) para la cual se generarán títulos."
    )
    target_social_network: Optional[str] = Field(
        None, 
        description="Opcional: Red social específica para la que se desean los títulos (ej. 'Twitter', 'LinkedIn').",
        examples=["Twitter", "Blog Post"]
    )
    number_of_titles: int = Field( # Lo hacemos mandatorio con default para que siempre sepamos cuántos pedir
        default=3, 
        ge=1,
        le=5, # Un límite razonable para sugerencias de títulos
        description="Número de títulos diferentes a generar."
    )

    class Config:
        from_attributes = True
        # Para Pydantic v1.x (json_schema_extra)
        # json_schema_extra = {
        #     "example": {
        #         "full_content_idea_text": "HOOK::¿Cansado de que la burocracia te coma el tiempo?...\nDESCRIPTION::Un video corto y dinámico que muestra cómo la automatización IA transforma problemas...\nFORMAT::Video Corto Vertical",
        #         "target_social_network": "Instagram",
        #         "number_of_titles": 3
        #     }
        # }
        # Para Pydantic v2.x (model_config con json_schema_extra)
        model_config = {
            "json_schema_extra": {
                "examples": [{
                    "full_content_idea_text": "HOOK::¿Cansado de que la burocracia te coma el tiempo?...\nDESCRIPTION::Un video corto y dinámico que muestra cómo la automatización IA transforma problemas...\nFORMAT::Video Corto Vertical",
                    "target_social_network": "Instagram",
                    "number_of_titles": 3
                }]
            }
        }


class GeneratedTitlesResponse(BaseModel):
    """Respuesta del endpoint que devuelve una lista de títulos generados."""
    titles: List[str]
    original_full_idea_text: str # Devolver el texto completo de la idea para referencia

    class Config:
        from_attributes = True

# --- FIN NUEVOS MODELOS ---


# -------------------------------------------------------------------------------------------------------------
# Modelos para la Generación de CAPTIONS para IMÁGENES
# -------------------------------------------------------------------------------------------------------------

class GenerateSingleImageCaptionRequest(BaseModel):
    """Petición para generar un caption para una publicación de imagen única."""
    
    # --- CAMPOS DE OVERRIDE DEL USUARIO ---
    voice_tone: Optional[str] = Field(
        None, 
        max_length=100, 
        description="Tono de voz específico para esta generación. Si se proporciona, sobreescribe la configuración de la organización."
    )
    content_length: Optional[str] = Field(
        None, 
        max_length=100,
        description="Preferencia de longitud para esta generación. Ejemplo: 'Corto', 'Medio (Ej: Post de Instagram/Facebook)'."
    )
 
    # --- CAMPOS DE CONTENIDO BASE ---
    title: Optional[str] = Field(
        None, 
        max_length=255,
        description="Título provisto por el usuario. Si se proporciona, se usará este en lugar de uno generado por IA."
    )
    prompt_id: Optional[UUID] = Field(None, description="ID del prompt de IA usado, si aplica.")
    generation_group_id: Optional[UUID] = Field(None, description="ID para agrupar varias generaciones de posts.")
    original_post_id: Optional[UUID] = Field(None, description="ID del post original si este es una variación.")
    
    # --- CAMPOS DE CONTEXTO Y TRAZABILIDAD
    main_idea: Optional[str] = Field(
        None, 
        description="Idea principal, tema o mensaje clave que la imagen busca transmitir.",
        examples=["Lanzamiento de nuestro nuevo producto ecológico"]
    )
    image_description: Optional[str] = Field(
        None,
        description="Breve descripción de lo que se ve en la imagen.",
        examples=["Un primer plano de nuestro producto X en un entorno natural."]
    )
    target_social_network: str = Field(
        ..., 
        description="Red social destino para esta publicación.",
        examples=["Instagram", "LinkedIn"]
    )
    call_to_action: Optional[str] = Field(
        None,
        description="Opcional: Llamado a la acción específico.",
        examples=["Más información en el enlace de la bio."]
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Cualquier otra instrucción relevante para la IA.",
        examples=["Mencionar nuestra oferta especial de verano."]
    )

    class Config:
        from_attributes = True
        model_config = {
            "json_schema_extra": {
                "examples": [
                    {
                        "title": "¡Nuestro Nuevo Ebook ya está Aquí!", # Ejemplo con el nuevo campo
                        "main_idea": "Promocionar nuestro nuevo ebook sobre marketing digital.",
                        "image_description": "Una persona leyendo un ebook en una tablet.",
                        "target_social_network": "LinkedIn",
                        "call_to_action": "Descarga tu copia gratuita (enlace en bio).",
                        "additional_notes": "Enfocarse en los beneficios para pequeñas empresas.",
                        "generation_group_id": "7118415c-ea3b-4926-97cd-9750e0b402d7" # Ejemplo con UUID
                    }
                ]
            }
        }


class SingleImageCaptionResponse(BaseModel): # Respuesta si solo devuelves el caption
    """Respuesta con el caption generado para una imagen."""
    generated_caption: str
    prompt_summary: Optional[Dict] = Field(None, description="Resumen de los inputs usados para generar el caption.")
    # Podrías añadir otros campos si el LLM los devuelve, como keywords sugeridas para el caption.

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------------------------------------------
# Modelos para la Generación de IMÁGENES desde Texto
# -------------------------------------------------------------------------------------------------------------

class ImageGenerationRequest(BaseModel):
    """Petición para generar una imagen desde un prompt de texto."""
    prompt: str = Field(..., min_length=3, max_length=1000, description="Prompt de texto para generar la imagen.")
    # aspect_ratio: Optional[str] = Field("1:1", description="Relación de aspecto deseada, ej: '1:1', '16:9'")
    # number_of_images: Optional[int] = Field(1, ge=1, le=4, description="Número de imágenes a generar.")
    # style_preset: Optional[str] = Field(None, description="Estilo artístico predefinido, ej: 'photographic', 'digital-art'")

    class Config:
        from_attributes = True
        # Para Pydantic v2:
        # model_config = {
        #     "json_schema_extra": {
        #         "examples": [{"prompt": "Un gato astronauta en Marte, estilo pintura al óleo."}]
        #     }
        # }


class ImageGenerationResponse(BaseModel):
    """Respuesta del endpoint de generación de imagen."""
    image_url: Optional[HttpUrl] = Field(None, description="URL pública de la imagen generada y almacenada.")
    image_base64: Optional[str] = Field(None, description="Imagen generada codificada en Base64 (si no se sube a storage).")
    prompt_used: str = Field(description="El prompt que se utilizó para generar la imagen.")
    error_message: Optional[str] = Field(None, description="Mensaje de error si la generación o subida falló.")
    # storage_path: Optional[str] = Field(None, description="Ruta en el bucket de almacenamiento donde se guardó la imagen.")

    class Config:
        from_attributes = True


# --- Modelo ANTIGUO para ideas (solo títulos) ---
# Puedes eliminarlo si ya no lo usas en ningún endpoint.
# Si lo mantienes, asegúrate de que ningún endpoint nuevo lo esté usando por error.
# class ContentIdeaResponse(BaseModel):
#     titles: List[str]