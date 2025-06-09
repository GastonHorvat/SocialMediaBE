# app/services/ai_image_generator.py
import base64
import logging
import uuid as uuid_pkg # Renombrado para evitar conflicto con el tipo UUID
from typing import Optional, Tuple, Dict, Any # Asegúrate que Dict esté
from uuid import UUID # Tipo UUID para type hints


# Importaciones de OpenAI (ajusta según tu configuración)
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError, OpenAIError
from app.core.config import settings # Para OPENAI_API_KEY y otras configuraciones de IA

# Importaciones de Supabase y Servicios
from app.db.supabase_client import SupabaseClient # Tipo para el cliente de Supabase
from app.services import storage_service # Nuestro servicio de storage
from app.services.ai_prompt_helpers import get_brand_identity_context

# --- Configuración del Logger ---
logger = logging.getLogger(__name__)

# --- Cliente de OpenAI (Singleton) ---
# (Asegúrate de que esta lógica esté aquí o sea importable si está en otro módulo de utils/config de IA)
_openai_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> AsyncOpenAI:
    """
    Obtiene o inicializa el cliente asíncrono de OpenAI.
    Lee la API key desde la configuración del proyecto.
    """
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY: # Asume que OPENAI_API_KEY está en tu objeto settings
            logger.error("OPENAI_API_KEY no está configurada en settings.")
            raise ValueError("OPENAI_API_KEY no está configurada para el servicio de IA.")
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Cliente AsyncOpenAI para generación de imágenes inicializado.")
    return _openai_client

# =======================================================================================
# SECCIÓN 1: GENERACIÓN DE IMAGEN BASE64 (Función de bajo nivel)
# Esta función es la base para las demás; interactúa directamente con la API de OpenAI.
# =======================================================================================
async def generate_image_base64_only(
    prompt_text: str,
    style_context: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    final_prompt = prompt_text
    if style_context:
        final_prompt = f"{prompt_text}. Estilo visual: {style_context}"
    
    logger.info(f"Solicitud a OpenAI con prompt final: '{final_prompt[:150]}...'")
    try:
        client = get_openai_client()
        response = await client.images.generate(
            model=settings.OPENAI_IMAGE_MODEL,         # <--- USAR SETTINGS
            prompt=final_prompt,
            size=settings.OPENAI_IMAGE_SIZE,           # <--- USAR SETTINGS
            quality=settings.OPENAI_IMAGE_QUALITY,     # <--- USAR SETTINGS
            # style=settings.OPENAI_IMAGE_STYLE, # Si añades este setting
            n=1,
            response_format="b64_json"
        )
        # ... (resto de la lógica de la función con manejadores de error) ...
        if response.data and len(response.data) > 0 and response.data[0].b64_json:
            return response.data[0].b64_json, None
        # ... (Manejo de error si no hay b64_json)
        err_msg = "OpenAI generó una respuesta pero no contenía datos de imagen b64_json."
        logger.warning(f"{err_msg} Respuesta OpenAI: {response.model_dump_json(indent=2) if response else 'None'}")
        return None, err_msg
    except APIConnectionError as e: # COPIA TUS MANEJADORES DE ERROR COMPLETOS AQUÍ
        logger.error(f"Error de conexión con OpenAI API (base64_only): {e}", exc_info=True)
        return None, f"Error de conexión al generar imagen con IA: {str(e)}"
    except RateLimitError as e:
        logger.error(f"Límite de tasa excedido con OpenAI API (base64_only): {e}", exc_info=True)
        return None, f"Límite de solicitudes excedido con la IA. Detalle: {str(e)}"
    except APIStatusError as e:
        logger.error(f"Error de estado de OpenAI API (base64_only) - Status: {e.status_code}, Mensaje: {e.message}", exc_info=True)
        specific_detail = e.message
        if e.body and isinstance(e.body, dict) and 'error' in e.body and isinstance(e.body['error'], dict) and 'message' in e.body['error']:
            specific_detail = e.body['error']['message']
        return None, f"Error de la API de IA (código: {e.status_code}): {specific_detail}"
    except OpenAIError as e:
        logger.error(f"Error genérico de OpenAI (base64_only): {e}", exc_info=True)
        return None, f"Ocurrió un error con la librería de IA al generar la imagen. Detalle: {str(e)}"
    except Exception as e:
        logger.error(f"Error inesperado generando imagen (base64_only): {e}", exc_info=True)
        return None, f"Ocurrió un error inesperado al generar la imagen (base64_only). Detalle: {str(e)}"

# =======================================================================================
# SECCIÓN 2: GENERAR IMAGEN PARA LA CARPETA DE TRABAJO '/wip/'
# Esta función se usará para el endpoint `POST /posts/{post_id}/generate-preview-image`.
# Llama a `generate_image_base64_only`, decodifica, y sube a la carpeta '/wip/' en `post_previews`.
# =======================================================================================
async def generate_and_upload_ai_image_to_wip(
    prompt_text: str,
    organization_id: UUID,
    post_id: UUID,
    supabase_client: SupabaseClient,

) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    # Retorna: (public_wip_url, wip_storage_path, wip_extension, wip_content_type, error_message)
    
    logger.info(f"Iniciando generación de imagen IA para WIP (post: {post_id}), prompt: '{prompt_text[:100]}...'")
    
    # Paso 1: Generar la imagen como Base64
    b64_image_data, ai_error = await generate_image_base64_only(
        prompt_text=prompt_text
        # , openai_model_name=openai_model_name, image_size=image_size, image_quality=image_quality # Si pasas params
    )
    
    if ai_error or not b64_image_data:
        logger.error(f"Fallo en generate_image_base64_only para WIP (post {post_id}): {ai_error}")
        return None, None, None, None, ai_error or "La IA no devolvió datos de imagen base64."

    # Paso 2: Decodificar Base64 a bytes y determinar tipo/extensión
    try:
        image_bytes = base64.b64decode(b64_image_data)
        # DALL-E con response_format="b64_json" devuelve imágenes PNG.
        img_extension = "png"
        img_content_type = "image/png"
        logger.debug(f"Imagen decodificada para WIP (post {post_id}), {len(image_bytes)} bytes, tipo: {img_content_type}")
    except (TypeError, ValueError) as e_decode:
        logger.error(f"Error decodificando imagen base64 para WIP (post {post_id}): {e_decode}", exc_info=True)
        return None, None, None, None, "Error procesando datos de imagen generada (decodificación fallida)."
    except Exception as e_unexp_decode: # Por si acaso
        logger.error(f"Error inesperado decodificando para WIP (post {post_id}): {e_unexp_decode}", exc_info=True)
        return None, None, None, None, "Error inesperado al decodificar imagen."


    # Paso 3: Definir la ruta de almacenamiento en la carpeta '/wip/'
    # La limpieza de la carpeta WIP la hará el router ANTES de llamar a esta función.
    active_wip_storage_path = storage_service.get_wip_image_storage_path(
        organization_id=organization_id,
        post_id=post_id,
        extension=img_extension
    )
    
    # Paso 4: Subir los bytes de la imagen a la carpeta '/wip/'
    public_url, uploaded_path, upload_error = await storage_service.upload_file_bytes_to_storage(
        supabase_client=supabase_client,
        bucket_name=storage_service.POST_PREVIEWS_BUCKET, # Bucket de previews/wip
        file_path_in_bucket=active_wip_storage_path,
        file_bytes=image_bytes,
        content_type=img_content_type,
        upsert=True, # Importante para sobrescribir si la limpieza previa falló por alguna razón
        add_timestamp_to_url=True # Para que la URL de preview no sea cacheada por el navegador
    )

    if upload_error or not public_url or not uploaded_path:
        logger.error(f"Error subiendo imagen IA generada a WIP (post {post_id}, path {active_wip_storage_path}): {upload_error}")
        return None, None, None, None, upload_error or "Error desconocido al guardar imagen en WIP."

    logger.info(f"Imagen IA para WIP (post {post_id}) subida a {uploaded_path}. URL: {public_url}")
    return public_url, uploaded_path, img_extension, img_content_type, None

# =======================================================================================
# SECCIÓN 3: GENERAR IMAGEN Y SUBIR A UBICACIÓN FINAL (Para `ai_router.py`)
# Esta función es usada por tu endpoint existente `POST /ai/posts/{post_id}/generate-image`.
# Genera una imagen y la sube directamente a `post_media` (la ubicación final).
# MODIFICADA para devolver también el `storage_path` y usar el `storage_service`.
# =======================================================================================
async def generate_image_from_prompt(
    prompt_text: str,
    organization_id: UUID,
    post_id: UUID,
    supabase_client: SupabaseClient,
    org_settings: Dict[str, Any], # Parámetro que ya añadimos
    openai_model_name: str = "dall-e-3", # Estos son opcionales
    image_size: str = "1024x1024",
    image_quality: str = "standard"
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Genera una imagen usando IA, la sube a la ubicación FINAL en `post_media`,
    y devuelve la URL pública y la ruta de almacenamiento de la imagen final.
    """
    logger.info(f"Iniciando generación de imagen IA para ubicación FINAL (post: {post_id})")

    # --- LÓGICA DE CONTEXTO ---
    brand_context = get_brand_identity_context(org_settings)
    # Creamos un string simple con el tono y la personalidad para el estilo visual
    image_style_context = f"{brand_context.get('communication_tone', '')}, {brand_context.get('personality_tags_str', '')}"
    # --- FIN LÓGICA DE CONTEXTO ---

    # Paso 1: Generar la imagen como Base64, pasando el contexto
    b64_image_data, ai_error = await generate_image_base64_only(
        prompt_text=prompt_text,
        style_context=image_style_context
    )
    
    # Esta es la única llamada que necesitamos. El bloque duplicado se elimina.

    if ai_error or not b64_image_data:
        logger.error(f"Fallo en generate_image_base64_only para imagen FINAL (post {post_id}): {ai_error}")
        return None, None, ai_error or "La IA no devolvió datos de imagen base64."

    # Paso 2: Decodificar Base64...
    try:
        image_bytes = base64.b64decode(b64_image_data)
        img_extension = "png"
        img_content_type = "image/png"
        logger.debug(f"Imagen decodificada para FINAL (post {post_id}), {len(image_bytes)} bytes, tipo: {img_content_type}")
    except (TypeError, ValueError) as e_decode:
        logger.error(f"Error decodificando imagen base64 para FINAL (post {post_id}): {e_decode}", exc_info=True)
        return None, None, "Error procesando datos de imagen generada (decodificación fallida)."
    
    # ... (El resto de la función (pasos 3 y 4) permanece igual) ...
    # Paso 3: Definir la ruta de almacenamiento FINAL en `post_media`
    unique_image_filename = f"{uuid_pkg.uuid4()}.{img_extension}"
    final_storage_path = storage_service.get_post_media_storage_path(
        organization_id=organization_id,
        post_id=post_id,
        final_filename_with_extension=unique_image_filename
    )
    
    # Paso 4: Subir los bytes de la imagen a `post_media`
    public_url, uploaded_path, upload_error = await storage_service.upload_file_bytes_to_storage(
        supabase_client=supabase_client,
        bucket_name=storage_service.POST_MEDIA_BUCKET,
        file_path_in_bucket=final_storage_path,
        file_bytes=image_bytes,
        content_type=img_content_type,
        upsert=False,
        add_timestamp_to_url=False
    )

    if upload_error or not public_url or not uploaded_path:
        logger.error(f"Error subiendo imagen IA generada a FINAL (post {post_id}, path {final_storage_path}): {upload_error}")
        return None, None, upload_error or "Error desconocido al guardar imagen final."

    logger.info(f"Imagen IA para FINAL (post {post_id}) subida a {uploaded_path}. URL: {public_url}")
    return public_url, uploaded_path, None