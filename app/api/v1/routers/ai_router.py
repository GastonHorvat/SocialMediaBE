# app/api/v1/routers/ai_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, Path 
from pydantic import BaseModel # No parece usarse directamente aquí, pero es común en modelos
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging # Usas logger, así que lo mantengo

from app.db.supabase_client import get_supabase_client, SupabaseClient
from app.api.v1.dependencies.auth import get_current_user, TokenData
# from app.core.config import settings # No se usa directamente si la inicialización de IA es en startup

# Modelos de IA y Posts
from app.models.ai_models import (
    ContentIdeasResponse, # Cambiado de ContentIdeaResponse para el nuevo formato
    GeneratedIdeaDetail,  # Nuevo modelo para la estructura de una idea
    GenerateSingleImageCaptionRequest,
    ImageGenerationRequest, 
    ImageGenerationResponse, 
    GenerateTitlesFromFullIdeaRequest, # <<< NUEVO MODELO DE PETICIÓN
    GeneratedTitlesResponse          # <<< NUEVO MODELO DE RESPUESTA
)
from app.models.post_models import PostResponse, PostCreate

# Servicios de IA
from app.services.ai_content_generator import (
    build_prompt_for_ideas,
    generate_text_with_gemini,
    parse_delimited_text_to_ideas, # ASUMIENDO QUE ESTA ES LA NUEVA FUNCIÓN DE PARSEO PARA IDEAS
    build_prompt_for_single_image_caption,
    parse_title_and_caption_from_llm,
    create_draft_post_from_ia,
    build_dalle_prompt_from_post_data, # Para la imagen automática del post
    build_prompt_for_titles,        # <<< NUEVA FUNCIÓN DE SERVICIO
    parse_lines_to_list             # <<< NUEVA FUNCIÓN DE PARSEO (o tu parse_gemini_idea_titles renombrada)
)
from app.services.ai_image_generator import (
    generate_image_from_prompt, # Genera, sube y devuelve URL
    generate_image_base64_only  # Solo devuelve base64
)

from postgrest.exceptions import APIError

router = APIRouter()
logger = logging.getLogger(__name__) # Correcto


# --- FUNCIÓN HELPER ---
async def get_organization_settings(
    organization_id: UUID,
    supabase: SupabaseClient
) -> Dict[str, Any]: # Esta función se ve bien
    if not organization_id:
        logger.warning("get_organization_settings fue llamado sin organization_id.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de organización no proporcionado para obtener la configuración.")
    try:
        response = supabase.table("organization_settings").select("*").eq("organization_id", str(organization_id)).maybe_single().execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron configuraciones de IA para la organización ID: {organization_id}. Por favor, configúralas."
            )
        return response.data
    except APIError as e_db:
        logger.error(f"APIError en get_organization_settings para org {organization_id}: {e_db.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error al contactar la base de datos para configuraciones de IA.")
    except Exception as e:
        logger.error(f"Error inesperado en get_organization_settings para org {organization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al obtener la configuración de la organización.")


# --- ENDPOINTS DE GENERACIÓN DE TEXTO ---
@router.post(
    "/content-ideas",
    response_model=ContentIdeasResponse, # Usar el nuevo modelo de respuesta
    summary="Generar Ideas de Contenido Detalladas con IA",
    description="Genera 3 ideas conceptuales para posts (con gancho, descripción y formato) basadas en la configuración de la organización.",
    tags=["AI Content Generation - Ideas"]
)
async def generate_content_ideas_endpoint(
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa para generar ideas.")
    
    org_settings: Dict[str, Any] # Declarar tipo para claridad
    try:
        # logger.debug(f"DEBUG_IDEAS_EP: Obteniendo settings para organization_id='{current_user.organization_id}'")
        org_settings = await get_organization_settings(current_user.organization_id, supabase)
        # logger.debug(f"DEBUG_IDEAS_EP: Org settings obtenidos: {org_settings}")
    except HTTPException as e:
        raise e # Re-lanzar HTTPExceptions de get_organization_settings
    # No es necesario capturar APIError/Exception aquí de nuevo si get_organization_settings ya las convierte a HTTPException

    # Validar que los settings necesarios para el prompt estén presentes
    if not org_settings.get('ai_brand_name') or not org_settings.get('ai_brand_industry'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La configuración de IA de la organización (nombre de marca, industria) debe estar completa para generar ideas.")

    # --- El código desde aquí está DENTRO del scope donde org_settings está definido ---
    prompt = build_prompt_for_ideas(org_settings) 
    
    # logger.debug(f"DEBUG_IDEAS_EP: Prompt generado para LLM (longitud: {len(prompt)} chars). Primeros 500 chars:\n{prompt[:500]}")
    # if len(prompt) > 500:
    #      logger.debug(f"DEBUG_IDEAS_EP: ... (prompt continúa) ...")

    llm_response_text: str = ""
    try:
        llm_response_text = await generate_text_with_gemini(prompt)
        # logger.debug(f"DEBUG_IDEAS_EP: Respuesta cruda del LLM (longitud: {len(llm_response_text)} chars):\n{llm_response_text}")
    except RuntimeError as e_gemini:
        logger.error(f"RuntimeError desde LLM para ideas: {e_gemini}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e_gemini))
    except Exception as e_llm:
        logger.error(f"Excepción inesperada llamando al LLM para ideas: {e_llm}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado al generar ideas con IA.")
    
    # Usar la función de parseo para el formato de texto delimitado
    parsed_ideas: List[GeneratedIdeaDetail] = parse_delimited_text_to_ideas(llm_response_text)
    
    # logger.debug(f"DEBUG_IDEAS_EP: Ideas parseadas (objetos GeneratedIdeaDetail): {parsed_ideas}")

    if not parsed_ideas: # Si la lista está vacía después del parseo
        logger.warning(f"LLM no devolvió ideas válidas o el parseo falló para ideas. Raw: '{llm_response_text}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="La IA no pudo generar ideas o la respuesta fue inválida.")
            
    return ContentIdeasResponse(ideas=parsed_ideas)

@router.post(
    "/generate-titles-from-idea",
    response_model=GeneratedTitlesResponse,
    summary="Generar Títulos para una Idea de Contenido con IA",
    description="Recibe el texto de una idea de contenido y genera múltiples opciones de títulos basadas en esa idea y la configuración de la organización.",
    tags=["AI Content Generation - Titles"] # Nueva tag para agrupar
)
async def generate_titles_from_idea_endpoint(
    request_data: GenerateTitlesFromFullIdeaRequest, # Modelo de petición que definimos
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa para generar títulos.")

    org_settings: Optional[Dict[str, Any]] = None
    try:
        # logger.debug(f"Obteniendo settings para títulos, org_id='{current_user.organization_id}'")
        org_settings = await get_organization_settings(current_user.organization_id, supabase)
    except HTTPException as e:
        raise e
    except Exception as e_settings: # Captura genérica si get_organization_settings no la convierte
        logger.error(f"Error inesperado obteniendo org_settings para títulos: {e_settings}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener la configuración de la organización.")

    # Validar que los settings necesarios para el prompt de títulos estén presentes
    if not org_settings.get('ai_brand_name') or not org_settings.get('ai_brand_industry'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La configuración de IA (nombre de marca, industria) debe estar completa para generar títulos.")

    prompt = build_prompt_for_titles(org_settings, request_data)
    
    # logger.debug(f"Prompt para títulos (primeros 300): {prompt[:300]}...")

    llm_response_text: str = ""
    try:
        llm_response_text = await generate_text_with_gemini(prompt)
        # logger.debug(f"Respuesta LLM para títulos (cruda): {llm_response_text}")
    except RuntimeError as e_gemini:
        logger.error(f"RuntimeError desde LLM para títulos: {e_gemini}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e_gemini))
    except Exception as e_llm:
        logger.error(f"Excepción inesperada llamando al LLM para títulos: {e_llm}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado al generar títulos con IA.")
    
    # Usamos la función genérica parse_lines_to_list para obtener los títulos,
    # ya que el prompt GENERATE_TITLES_FROM_IDEA_V1 pide un título por línea.
    # Pasamos request_data.number_of_titles para limitar el resultado.
    generated_titles = parse_lines_to_list(llm_response_text, max_items=request_data.number_of_titles)
    
    # logger.debug(f"Títulos parseados: {generated_titles}")

    if not generated_titles:
        logger.warning(f"LLM no devolvió títulos o el parseo falló. Raw: '{llm_response_text}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="La IA no pudo generar títulos o la respuesta fue inválida.")
        
    return GeneratedTitlesResponse(
        titles=generated_titles,
        original_full_idea_text=request_data.full_content_idea_text # Devolvemos la idea original
    )

# --- FIN NUEVO ENDPOINT ---

@router.post(
    "/generate-single-image-caption",
    response_model=PostResponse,
    summary="Generar Título y Caption para Imagen y Guardar Borrador",
    description="Genera un título y un caption para una imagen, y guarda el resultado como un post borrador.",
    tags=["AI Content Generation - Text", "Posts"]
)
async def generate_caption_and_save_post_endpoint( # Renombrado
    request_data: GenerateSingleImageCaptionRequest,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client),
):
    if not current_user.organization_id or not current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no activo en organización o ID de usuario faltante.")

    org_settings = await get_organization_settings(current_user.organization_id, supabase)
    if not org_settings.get('ai_brand_name') or not org_settings.get('ai_brand_industry'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configuración de IA (nombre de marca, industria) incompleta.")

    prompt = build_prompt_for_single_image_caption(org_settings, request_data)
    try:
        llm_full_response_text = await generate_text_with_gemini(prompt)
    except RuntimeError as e_gemini:
        logger.error(f"RuntimeError desde LLM para caption: {e_gemini}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e_gemini))
    
    if not llm_full_response_text or not llm_full_response_text.strip():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="IA no pudo generar contenido para caption.")

    parsed_content = parse_title_and_caption_from_llm(llm_full_response_text)
    generated_title = parsed_content.get("title")
    generated_caption = parsed_content.get("content_text")

    if not generated_caption: # El caption es mandatorio
        logger.error(f"Parseo de caption fallido. Raw: '{llm_full_response_text}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="IA no generó el formato de caption esperado.")

    post_to_create = PostCreate(
        title=generated_title,
        content_text=generated_caption.strip(),
        social_network=request_data.target_social_network,
        content_type="image", # Asume que es para una imagen
    )
    try:
        newly_created_post_data = await create_draft_post_from_ia(
            supabase_client=supabase,
            author_id=current_user.user_id,
            organization_id=current_user.organization_id,
            post_create_data=post_to_create
        )
        return PostResponse.model_validate(newly_created_post_data)
    except RuntimeError as e_db:
        logger.error(f"RuntimeError guardando post de caption: {e_db}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e_db))


# --- ENDPOINTS DE GENERACIÓN DE IMAGEN ---

# Modelo para el cuerpo de la solicitud del nuevo endpoint
class GenerateImageForPostRequestBody(BaseModel):
    prompt: str

@router.post(
    "/posts/{post_id}/generate-image",
    response_model=PostResponse,
    summary="Generar Imagen para Post (Automática), Subirla y Asociarla",
    description="Genera automáticamente una imagen basada en el contenido de un post existente, "
                "la sube al almacenamiento, y actualiza el post con la URL de la imagen.",
    tags=["AI Image Generation", "Posts"]
)
async def generate_auto_image_for_post_endpoint( # Renombrado para reflejar que es "auto"
    post_id: UUID = Path(..., description="El ID del post existente"),
    # request_body: GenerateImageForPostRequestBody = Body(...), # <--- ELIMINAR ESTA LÍNEA
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    logger.info(f"Solicitud para generar imagen AUTOMÁTICA para post ID: {post_id} por usuario {current_user.user_id}")
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")

    # 1. Obtener el contenido del post (título, content_text, social_network)
    post_data_for_image: Optional[Dict[str, Any]] = None
    try:
        # Seleccionar los campos necesarios: title, content_text, social_network
        post_res = supabase.table("posts") \
            .select("title, content_text, social_network, organization_id") \
            .eq("id", str(post_id)) \
            .maybe_single() \
            .execute()
            
        if not post_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post con ID {post_id} no encontrado.")
        if str(post_res.data['organization_id']) != str(current_user.organization_id): # Verificar pertenencia
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El post no pertenece a su organización.")
        post_data_for_image = post_res.data
    except APIError as e_check_api:
        logger.error(f"APIError obteniendo post {post_id} para prompt de imagen: {e_check_api.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error de BD obteniendo datos del post.")
    except Exception as e_check:
        logger.error(f"Error inesperado obteniendo post {post_id} para prompt de imagen: {e_check}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno obteniendo datos del post.")

    # Extraer los datos necesarios para el prompt
    post_title = post_data_for_image.get("title")
    post_content = post_data_for_image.get("content_text", "") # Default a string vacío si es None
    social_network = post_data_for_image.get("social_network", "una red social general") # Default

    if not post_content: # Si el contenido del post es vital para el prompt
        logger.warning(f"Post {post_id} no tiene content_text para generar un prompt de imagen significativo.")
        # Podrías usar solo el título o devolver un error si el contenido es crucial.
        # Por ahora, la función build_dalle_prompt_from_post_data lo manejará con un excerpt="contenido no especificado".
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El contenido del post es necesario para generar la imagen y está vacío.")


    # 2. Construir el prompt para DALL-E usando los datos del post
    dalle_prompt = build_dalle_prompt_from_post_data(
        post_title=post_title,
        post_content_text=post_content,
        social_network=social_network
        # Futuro: pasar org_settings aquí para influir en el estilo del prompt o de la imagen
    )

    # 3. Llamar al servicio que genera la imagen con DALL-E, la sube y devuelve la URL
    public_image_url, storage_path_final, error_msg = await generate_image_from_prompt(
        prompt_text=dalle_prompt, # <--- USANDO EL PROMPT CONSTRUIDO
        organization_id=current_user.organization_id,
        post_id=post_id,
        supabase_client=supabase
    )

    # 4. Manejo de errores y actualización del post (esta parte es igual que antes)
    if error_msg:
        logger.error(f"Fallo en generate_image_from_prompt para post {post_id} con prompt automático: {error_msg}")
        status_code_err = status.HTTP_502_BAD_GATEWAY
        if "bloqueado" in error_msg.lower(): status_code_err = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code_err, detail=f"Proceso de generación/subida de imagen falló: {error_msg}")

    if not public_image_url:
        logger.error(f"No se obtuvo URL de imagen para post {post_id} (prompt automático) y no hubo error explícito.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo obtener la URL de la imagen procesada.")

    try:
        logger.info(f"Actualizando post '{post_id}' con media_url (prompt automático): {public_image_url}")
        update_response = supabase.table("posts") \
            .update({"media_url": public_image_url}) \
            .eq("id", str(post_id)) \
            .eq("organization_id", str(current_user.organization_id)) \
            .execute()
        
        if not update_response.data or len(update_response.data) == 0:
            logger.error(f"Post '{post_id}' (prompt automático) no se actualizó. Respuesta DB: {update_response}")
            current_post_res = supabase.table("posts").select("*").eq("id", str(post_id)).single().execute()
            if current_post_res.data: return PostResponse.model_validate(current_post_res.data)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} no encontrado tras actualización.")
        
        logger.info(f"Post '{post_id}' (prompt automático) actualizado con nueva media_url.")
        return PostResponse.model_validate(update_response.data[0])

    except APIError as db_exc_api:
        logger.error(f"APIError de Supabase actualizando post '{post_id}' (prompt automático): {db_exc_api.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de BD (API) al actualizar post: {db_exc_api.message}")
    except Exception as db_exc:
        logger.error(f"Error inesperado actualizando post '{post_id}' (prompt automático): {db_exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al actualizar post: {str(db_exc)}")


@router.post(
    "/generate-image", # URL: /api/v1/ai/generate-image
    response_model=ImageGenerationResponse,
    summary="Generar una imagen con IA (Devuelve Base64)",
    description="Crea una imagen basada en un prompt y la devuelve codificada en Base64 (PNG). NO la guarda ni asocia a un post.",
    tags=["AI Image Generation"]
)
async def generate_image_only_endpoint(
    request_body: ImageGenerationRequest = Body(...),
    # current_user: TokenData = Depends(get_current_user) # Puedes añadir auth si es necesario
):
    logger.info(f"Solicitud de generación de imagen (solo base64) con prompt: '{request_body.prompt[:100]}...'")

    # --- CAMBIO EN LA LLAMADA ---
    # Llamar a la función que solo genera base64
    base64_image, error_message = await generate_image_base64_only(
        prompt_text=request_body.prompt
        # Aquí puedes pasar parámetros como openai_model_name, image_size, image_quality
        # si los añades al modelo ImageGenerationRequest y los pasas aquí.
    )
    # --- FIN DEL CAMBIO ---

    if error_message:
        logger.error(f"Error al generar imagen (solo base64) para prompt '{request_body.prompt[:100]}...': {error_message}")
        status_code_err = status.HTTP_502_BAD_GATEWAY # Default
        if "bloqueado" in error_message.lower() or "política de contenido" in error_message.lower():
            status_code_err = status.HTTP_400_BAD_REQUEST
        elif "configur" in error_message.lower() or "API key" in error_message.lower() or "Límite de solicitudes" in error_message.lower():
            status_code_err = status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=status_code_err, detail=error_message)

    if not base64_image:
        logger.error(f"No se generó imagen (solo base64) para '{request_body.prompt[:100]}...' y no hubo error explícito.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar la imagen y no se reportó un error específico.")

    return ImageGenerationResponse(
        image_base64=base64_image, # Ahora esto es correcto porque la función devuelve base64
        prompt_used=request_body.prompt
    )