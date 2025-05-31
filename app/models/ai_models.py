# app/models/ai_models.py
from pydantic import BaseModel, Field, HttpUrl 
from typing import Optional, List , Dict

class ContentIdeaResponse(BaseModel):
    titles: List[str]

# -------------------------------------------------------------------------------------------------------------
# Clase para la PETICIÓN de generar un caption para una imagen única.
# -------------------------------------------------------------------------------------------------------------
class GenerateSingleImageCaptionRequest(BaseModel):
    main_idea: Optional[str] = Field(
        None, 
        description="Idea principal, tema o mensaje clave que la imagen busca transmitir. Ayuda a la IA a enfocar el caption.",
        examples=["Lanzamiento de nuestro nuevo producto ecológico", "Celebrando el aniversario del equipo"]
    )
    image_description: Optional[str] = Field(
        None,
        description="Breve descripción de lo que se ve en la imagen (ej. 'mujer sonriendo usando laptop en cafetería', 'paisaje montañoso al atardecer'). Ayuda a la IA a conectar el texto con el visual.",
        examples=["Un primer plano de nuestro producto X en un entorno natural.", "Nuestro equipo colaborando en la oficina."]
    )
    target_social_network: str = Field( # Asumimos que la red social es requerida para un caption
        ..., # El ... indica que es requerido
        description="Red social destino para esta publicación (ej. 'Instagram', 'Facebook', 'LinkedIn').",
        examples=["Instagram", "LinkedIn"]
    )
    call_to_action: Optional[str] = Field(
        None,
        description="Opcional: Un llamado a la acción específico que te gustaría incluir (ej. 'Visita nuestra web', 'Comenta abajo').",
        examples=["Más información en el enlace de la bio.", "Regístrate hoy."]
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Cualquier otra instrucción o nota relevante para la IA al generar el caption.",
        examples=["Mencionar nuestra oferta especial de verano.", "Usar un tono más inspirador esta vez."]
    )

    class Config:
        json_schema_extra = { # Esto es para Pydantic v1, para v2 sería model_config y schema_extra
            "example": {
                "main_idea": "Promocionar nuestro nuevo ebook sobre marketing digital.",
                "image_description": "Una persona leyendo un ebook en una tablet, con gráficos de marketing de fondo.",
                "target_social_network": "LinkedIn",
                "call_to_action": "Descarga tu copia gratuita (enlace en bio).",
                "additional_notes": "Enfocarse en los beneficios para pequeñas empresas."
            }
        }
        # Si usas Pydantic v2:
        # model_config = {
        #     "json_schema_extra": {
        #         "examples": [ # Pydantic v2 prefiere una lista de ejemplos
        #             {
        #                 "main_idea": "Promocionar nuestro nuevo ebook sobre marketing digital.",
        #                 "image_description": "Una persona leyendo un ebook en una tablet, con gráficos de marketing de fondo.",
        #                 "target_social_network": "LinkedIn",
        #                 "call_to_action": "Descarga tu copia gratuita (enlace en bio).",
        #                 "additional_notes": "Enfocarse en los beneficios para pequeñas empresas."
        #             }
        #         ]
        #     }
        # }


# -------------------------------------------------------------------------------------------------------------
# Clase para la PETICIÓN de generar una imagen desde un prompt de texto.
# -------------------------------------------------------------------------------------------------------------
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000, description="Prompt de texto para generar la imagen.")
    # Podrías añadir más parámetros aquí si el modelo los soporta y quieres exponerlos
    # ej: aspect_ratio: Optional[str] = "1:1"
    #     number_of_images: Optional[int] = Field(1, ge=1, le=4)
    #     style_preset: Optional[str] = None # ej. "photographic", "digital-art"

    class Config:
        from_attributes = True # o orm_mode = True para v1
        # Ejemplo para Pydantic v2
        # model_config = {
        #     "json_schema_extra": {
        #         "examples": [{"prompt": "Un gato astronauta en Marte."}]
        #     }
        # }

# -------------------------------------------------------------------------------------------------------------
# Clase para la RESPUESTA de generación de imagen.
# -------------------------------------------------------------------------------------------------------------
class ImageGenerationResponse(BaseModel):
    image_url: Optional[HttpUrl] = None # Usar HttpUrl para validar que es una URL válida
    prompt_used: str
    error_message: Optional[str] = None
    # Podrías añadir el path en el bucket si fuera útil para el FE:
    # storage_path: Optional[str] = None

    class Config:
        from_attributes = True # o orm_mode = True para v1

# Aquí podrías añadir más modelos de respuesta para IA, por ejemplo para el caption generado:
class SingleImageCaptionResponse(BaseModel):
    generated_caption: str
    prompt_summary: Optional[Dict] = None # Resumen de los inputs usados para generar