# app/models/ai_models.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict

# -------------------------------------------------------------------------------------------------------------
# Modelos para la Generación de IDEAS DE CONTENIDO
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


# -------------------------------------------------------------------------------------------------------------
# Modelos para la Generación de CAPTIONS para IMÁGENES
# -------------------------------------------------------------------------------------------------------------

class GenerateSingleImageCaptionRequest(BaseModel):
    """Petición para generar un caption para una publicación de imagen única."""
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
        # Para Pydantic v1:
        # json_schema_extra = {
        #     "example": {
        #         "main_idea": "Promocionar nuestro nuevo ebook sobre marketing digital.",
        #         "image_description": "Una persona leyendo un ebook en una tablet.",
        #         "target_social_network": "LinkedIn",
        #         "call_to_action": "Descarga tu copia gratuita (enlace en bio).",
        #         "additional_notes": "Enfocarse en los beneficios para pequeñas empresas."
        #     }
        # }
        # Para Pydantic v2:
        model_config = {
            "json_schema_extra": {
                "examples": [
                    {
                        "main_idea": "Promocionar nuestro nuevo ebook sobre marketing digital.",
                        "image_description": "Una persona leyendo un ebook en una tablet.",
                        "target_social_network": "LinkedIn",
                        "call_to_action": "Descarga tu copia gratuita (enlace en bio).",
                        "additional_notes": "Enfocarse en los beneficios para pequeñas empresas."
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