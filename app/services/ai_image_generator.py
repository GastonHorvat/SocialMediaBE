# app/services/ai_image_generator.py
import base64
import logging
import asyncio
from typing import Optional, Tuple, Dict # Asegúrate que Dict esté
from uuid import UUID

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError, OpenAIError
from supabase import Client as SupabaseClient
from postgrest.exceptions import APIError as SupabaseAPIError

from app.core.config import settings # Para OPENAI_API_KEY

logger = logging.getLogger(__name__)

_openai_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> AsyncOpenAI:
    """Obtiene o inicializa el cliente asíncrono de OpenAI."""
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY no está configurada en settings.")
            raise ValueError("OPENAI_API_KEY no está configurada.")
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Cliente AsyncOpenAI inicializado.")
    return _openai_client

async def generate_image_base64_only(
    prompt_text: str,
    openai_model_name: str = "dall-e-3",
    image_size: str = "1024x1024",
    image_quality: str = "standard"
) -> Tuple[Optional[str], Optional[str]]: # (base64_image_string, error_message)
    """
    Genera una imagen usando OpenAI DALL-E y devuelve los datos de la imagen codificados en Base64.
    No interactúa con el almacenamiento.
    """
    try:
        client = get_openai_client()
        logger.info(f"Generando imagen (solo Base64) con DALL-E (modelo: '{openai_model_name}'), prompt: '{prompt_text[:100]}...'")
        
        response = await client.images.generate(
            model=openai_model_name,
            prompt=prompt_text,
            size=image_size,
            quality=image_quality,
            n=1,
            response_format="b64_json"
        )

        if response.data and len(response.data) > 0 and response.data[0].b64_json:
            b64_image_data = response.data[0].b64_json
            logger.info(f"Imagen (solo Base64) generada exitosamente por DALL-E (modelo: {openai_model_name}).")
            return b64_image_data, None
        else:
            logger.warning(f"DALL-E no devolvió datos b64_json (solo Base64). Respuesta: {response.model_dump_json(indent=2)}")
            return None, "La IA generó una respuesta pero no contenía datos de imagen b64_json."

    except APIConnectionError as e:
        logger.error(f"Error de conexión con OpenAI API (solo Base64): {e}", exc_info=True)
        return None, f"Error de conexión al generar imagen con IA: {str(e)}"
    except RateLimitError as e:
        logger.error(f"Límite de tasa excedido con OpenAI API (solo Base64): {e}", exc_info=True)
        return None, f"Límite de solicitudes excedido con la IA. Detalle: {str(e)}"
    except APIStatusError as e:
        logger.error(f"Error de estado de OpenAI API (solo Base64) - Status: {e.status_code}, Mensaje: {e.message}", exc_info=True)
        error_message = f"Error de la API de IA (código: {e.status_code}): {e.message}"
        if e.status_code == 400 and e.body and 'error' in e.body and 'message' in e.body['error']:
            specific_detail = e.body['error']['message']
            error_message = f"Error de la API de IA (código: {e.status_code}): {specific_detail}"
        return None, error_message
    except OpenAIError as e:
        logger.error(f"Error genérico de OpenAI (solo Base64): {e}", exc_info=True)
        return None, f"Ocurrió un error con la librería de IA al generar la imagen. Detalle: {str(e)}"
    except Exception as e:
        logger.error(f"Error inesperado generando imagen (solo Base64): {e}", exc_info=True)
        return None, f"Ocurrió un error inesperado al generar la imagen (solo Base64). Detalle: {str(e)}"


async def generate_image_from_prompt( # Esta es la que SÍ sube y devuelve URL
    prompt_text: str,
    organization_id: UUID,
    post_id: UUID,
    supabase_client: SupabaseClient,
    bucket_name: str = "content.flow.media",
    openai_model_name: str = "dall-e-3",
    image_size: str = "1024x1024", # Re-añadido para pasarlo a la función de base64
    image_quality: str = "standard" # Re-añadido para pasarlo a la función de base64
) -> Tuple[Optional[str], Optional[str]]: # (public_url, error_message)
    """
    Genera una imagen usando OpenAI DALL-E, la sube a Supabase Storage,
    y devuelve la URL pública de la imagen.
    """
    
    # 1. Generar la imagen usando la función que solo devuelve base64
    b64_image_data, ai_error = await generate_image_base64_only(
        prompt_text=prompt_text,
        openai_model_name=openai_model_name,
        image_size=image_size,
        image_quality=image_quality
    )
    
    if ai_error:
        logger.error(f"Error de IA generando base64 para post {post_id}: {ai_error}")
        return None, ai_error # Propagar el mensaje de error de la generación base64
    
    if not b64_image_data:
        logger.warning(f"No se generaron datos de imagen base64 por IA para post {post_id}.")
        return None, "La IA no devolvió datos de imagen."

    # 2. Decodificar de Base64 a bytes
    try:
        image_bytes = base64.b64decode(b64_image_data)
    except Exception as e:
        logger.error(f"Error decodificando imagen base64 para post '{post_id}': {e}", exc_info=True)
        return None, "Error procesando los datos de la imagen generada."

    # 3. Definir el path y subir a Supabase Storage
    file_extension = "png" 
    file_path_in_bucket = f"{str(organization_id)}/{str(post_id)}.{file_extension}"
    
    try:
        logger.info(f"Subiendo imagen a Supabase Storage: bucket='{bucket_name}', path='{file_path_in_bucket}' para post '{post_id}'")
        
        await asyncio.to_thread(
            supabase_client.storage.from_(bucket_name).upload,
            path=file_path_in_bucket,
            file=image_bytes,
            file_options={"content-type": f"image/{file_extension}", "upsert": "true"}
        )
        logger.info(f"Imagen subida exitosamente a Supabase Storage para post '{post_id}'.")

    except SupabaseAPIError as e:
        logger.error(f"Error de API Supabase al subir imagen para post '{post_id}': {e.message} (Code: {e.code}, Details: {e.details})", exc_info=True)
        return None, f"Error de API del almacenamiento al guardar la imagen: {e.message}"
    except Exception as e:
        logger.error(f"Error inesperado al subir imagen a Supabase Storage para post '{post_id}': {e}", exc_info=True)
        return None, f"Error inesperado al guardar la imagen generada en el almacenamiento: {str(e)}"

    # 4. Obtener la URL pública
    try:
        public_url_string = supabase_client.storage.from_(bucket_name).get_public_url(file_path_in_bucket)
        
        if not public_url_string or not isinstance(public_url_string, str) or not public_url_string.startswith("http"):
             logger.error(f"URL pública inválida obtenida de Supabase para post '{post_id}': {public_url_string}")
             return None, "No se pudo obtener una URL válida para la imagen almacenada."

        logger.info(f"URL pública obtenida para post '{post_id}': {public_url_string}")
        return public_url_string, None

    except SupabaseAPIError as e:
        logger.error(f"Error de API Supabase al obtener URL pública para post '{post_id}': {e.message} (Code: {e.code}, Details: {e.details})", exc_info=True)
        return None, f"Error de API del almacenamiento al obtener la dirección de la imagen: {e.message}"
    except Exception as e:
        logger.error(f"Error inesperado al obtener URL pública de Supabase Storage para post '{post_id}': {e}", exc_info=True)
        return None, f"Error inesperado al obtener la dirección de la imagen almacenada: {str(e)}"