# app/api/v1/routers/posts.py
# --------------------------------------------------------------------------- #
# 1. LIBRERÍAS ESTÁNDAR DE PYTHON
# --------------------------------------------------------------------------- #
import logging
import pytz
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid as uuid_pkg

# --------------------------------------------------------------------------- #
# 2. LIBRERÍAS DE TERCEROS
# --------------------------------------------------------------------------- #
from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, status, UploadFile
from postgrest.exceptions import APIError
from pydantic import HttpUrl

# --------------------------------------------------------------------------- #
# 3. IMPORTACIONES DE LA APLICACIÓN
# --------------------------------------------------------------------------- #
from app.api.v1.dependencies.auth import TokenData, get_current_user
from app.db.supabase_client import SupabaseClient, get_supabase_client
from app.models.post_models import (
    ConfirmWIPImageDetails,
    ContentTypeEnum,
    GeneratePreviewImageRequest,
    GeneratePreviewImageResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
)
from app.services import ai_image_generator, storage_service

# --- CONFIGURACIÓN DEL LOGGER (ASEGÚRATE DE TENERLA) ---
import logging
logger = logging.getLogger(__name__)

class DeletedFilterEnum(str, Enum):
    not_deleted = "not_deleted"
    deleted = "deleted"
    all = "all"

router = APIRouter()

@router.get(
    "/",
    response_model=List[Dict[str, Any]],
    summary="Obtener Lista de Posts (con filtros avanzados)",
    description="Devuelve una lista de posts del usuario autenticado dentro de su organización, con opciones para filtrar.",
    tags=["Posts"],
)
async def get_posts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado (ej. draft, approved)"),
    social_network: Optional[str] = Query(None, description="Filtrar por red social"),
    content_type: Optional[str] = Query(None, description="Filtrar por tipo de contenido"),
    date_from: Optional[date] = Query(None, description="Fecha desde (para created_at o scheduled_at)"),
    date_to: Optional[date] = Query(None, description="Fecha hasta (para created_at o scheduled_at)"),
    limit: int = Query(20, ge=1, le=100, description="Número de posts a devolver"),
    offset: int = Query(0, ge=0, description="Número de posts a saltar para paginación"),
    deleted_filter: DeletedFilterEnum = Query(
        DeletedFilterEnum.not_deleted,
        description="Filtrar posts por estado de borrado: "
                    "'not_deleted' (solo activos), "
                    "'deleted' (solo borrados), "
                    "'all' (todos)."
    ),
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    print(f"DEBUG get_posts: current_user.user_id='{current_user.user_id}', current_user.organization_id='{current_user.organization_id}', current_user.role='{current_user.role}'") # Añade esto
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id # Puede ser None
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)

        query = supabase.table("posts").select("*").eq("author_user_id", author_id_str)

        if org_id_uuid:
            query = query.eq("organization_id", str(org_id_uuid))
        else:
            # Si el usuario no tiene una organización activa, no debería ver ningún post.
            # Opcionalmente, podrías lanzar una HTTPException aquí.
            print(f"WARN: Usuario {author_id_str} sin organization_id activa, devolviendo lista vacía para get_posts.")
            return []

        if deleted_filter == DeletedFilterEnum.not_deleted:
            query = query.is_("deleted_at", None)
        elif deleted_filter == DeletedFilterEnum.deleted:
            query = query.not_.is_("deleted_at", None)
        # Para 'all', no se aplica filtro de deleted_at.

        if status_filter:
            query = query.eq("status", status_filter)
        if social_network:
            query = query.eq("social_network", social_network)
        if content_type:
            query = query.eq("content_type", content_type)
        if date_from:
            query = query.gte("created_at", str(date_from))
        if date_to:
            query = query.lte("created_at", str(date_to))

        query = query.order("created_at", desc=True).limit(limit).offset(offset)
        response = query.execute()

        posts_data = response.data # Esto es una lista de diccionarios
        if not posts_data:
            return []

        # Enriquecemos los datos manualmente
        for post in posts_data:
            content_type_key = post.get('content_type')
            if content_type_key:
                try:
                    post['content_type_display'] = ContentTypeEnum[content_type_key].value
                except KeyError:
                    post['content_type_display'] = content_type_key # Fallback
        
        return posts_data

    except Exception as e:
        print(f"Error fetching posts for user {author_id_str} in org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al obtener los posts. {str(e)}"
        )

@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un Nuevo Post",
    description="Crea un nuevo post asociado al usuario autenticado y su organización.",
    tags=["Posts"]
)
async def create_post(
    post_data: PostCreate,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"
@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un Nuevo Post",
    description="Crea un nuevo post asociado al usuario autenticado y su organización.",
    tags=["Posts"]
)
async def create_post(
    post_data: PostCreate,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    # --- VALIDACIÓN MANUAL DE content_type ---
    try:
        # Verificamos que el string del request es una clave válida en nuestro Enum
        ContentTypeEnum[post_data.content_type]
    except KeyError:
        valid_options = [e.name for e in ContentTypeEnum]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Valor inválido para 'content_type'. Las opciones válidas son: {valid_options}"
        )
    # --- FIN DE VALIDACIÓN ---

    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id

        if not org_id_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede crear el post: el usuario no está asociado a una organización activa."
            )

        # Usamos el model_dump que ya tenías, que convierte el objeto Pydantic a dict
        # y ahora `content_type` ya es un string validado ('IMAGE_POST', etc.)
        new_post_dict = post_data.model_dump(exclude_unset=True)
        
        # Aseguramos los IDs del autor y la organización
        new_post_dict["author_user_id"] = author_id_str
        new_post_dict["organization_id"] = str(org_id_uuid)

        # Insertar el nuevo post
        insert_response = supabase.table("posts").insert(new_post_dict).execute()
        
        if not insert_response.data or not isinstance(insert_response.data, list) or len(insert_response.data) == 0:
            logger.error(f"ERROR_POST_CREATE: La inserción del post no devolvió datos. Payload: {new_post_dict}. Respuesta: {insert_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear el post o no se obtuvieron los datos del post creado."
            )
        
        created_post_data_from_insert = insert_response.data[0]
        
        # Validamos el resultado para la respuesta.
        # Nuestro PostResponse ahora tiene el computed_field que añadirá `content_type_display`
        validated_post = PostResponse.model_validate(created_post_data_from_insert)
        return validated_post

    except HTTPException as http_exc:
        # Re-lanzamos las excepciones HTTP que nosotros mismos generamos (como la 422)
        raise http_exc
    except APIError as e:
        logger.error(f"APIError creando post para user {author_id_str} en org {org_id_for_log}: Code={getattr(e, 'code', 'N/A')}, Msg='{e.message}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos al crear el post: {e.message}"
        )
    except Exception as e:
        logger.error(f"Excepción inesperada creando post para user {author_id_str} en org {org_id_for_log}: {type(e).__name__} - {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al crear el post: {str(e)}"
        )

@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Obtener un Post Específico",
    description="Recupera un post por ID, si pertenece al usuario y su organización.",
    tags=["Posts"]
)
async def get_post_by_id(
    post_id: UUID = Path(..., description="El ID del post a recuperar"),
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id
        
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            # Si no hay organización, el post no puede pertenecer al usuario en una organización.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado o acceso denegado (usuario sin organización activa)."
            )

        query_builder = (
            supabase.table("posts")
            .select("*")
            .eq("id", str(post_id))
            .eq("author_user_id", author_id_str)
            .eq("organization_id", str(org_id_uuid)) # Seguro porque org_id_uuid está validado
            .is_("deleted_at", None)
            .single()
        )
        
        response = query_builder.execute()
        post_data = response.data

        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario/organización, o ha sido eliminado."
            )
        return PostResponse.model_validate(post_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error obteniendo post {post_id} para user {author_id_str} en org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al obtener el post: {str(e)}"
        )

@router.delete(
    "/{post_id}",
    response_model=PostResponse,
    summary="Borrar Lógicamente un Post",
    description="Marca un post como eliminado (soft delete), estableciendo 'deleted_at' y actualizando el 'status'.",
    tags=["Posts"]
)
async def soft_delete_post(
    post_id: UUID = Path(..., description="El ID del post a marcar como eliminado"),
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"
    
    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id
        
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"No se puede eliminar el post {post_id}: usuario sin organización activa."
            )

        now_utc = datetime.now(pytz.utc)
        update_payload = {
            "deleted_at": now_utc.isoformat(),
            "status": "deleted" 
            # "updated_at" debería ser manejado por el trigger de la DB
        }

        # --- CORRECCIÓN AQUÍ ---
        # Paso 1: Actualizar el post para marcarlo como borrado
        update_response = (
            supabase.table("posts")
            .update(update_payload)
            .eq("id", str(post_id))
            .eq("author_user_id", author_id_str)
            .eq("organization_id", str(org_id_uuid))
            .is_("deleted_at", None) # Solo borrar si no está ya borrado
            .execute()
        )
        
        # response.data de un update es una lista de los registros actualizados
        # si PostgREST está configurado para devolver la representación.
        # Si no se actualizó nada (porque no encontró la fila o ya estaba borrada), .data será [].
        if update_response.data and isinstance(update_response.data, list) and len(update_response.data) > 0:
            # El post actualizado (ahora con deleted_at y status='deleted')
            deleted_post_data_dict = update_response.data[0]
            return PostResponse.model_validate(deleted_post_data_dict)
        elif not update_response.data or len(update_response.data) == 0:
            # La condición .eq() o .is_("deleted_at", None) no encontró ninguna fila que actualizar.
            print(f"WARN_POST_DELETE: No se marcó como borrado el post {post_id} (usuario: {author_id_str}, org: {org_id_for_log}). Verifique si existe, pertenece al usuario/org, o si ya estaba borrado.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario/organización, o ya estaba eliminado."
            )
        else:
            # Caso inesperado
            print(f"ERROR_POST_DELETE: Respuesta inesperada del update (soft delete) para post {post_id}. Respuesta: {update_response}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al procesar el borrado del post.")
        # --- FIN DE LA CORRECCIÓN ---

    except HTTPException as http_exc:
        raise http_exc
    except APIError as e:
        print(f"ERROR_POST_DELETE: APIError soft-deleting post {post_id} para user {author_id_str} en org {org_id_for_log}: Code={getattr(e, 'code', 'N/A')}, Msg='{e.message}'")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error de base de datos al marcar el post como eliminado: {e.message}"
        )
    except Exception as e:
        print(f"ERROR_POST_DELETE: Excepción inesperada soft-deleting post {post_id} para user {author_id_str} en org {org_id_for_log}: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al marcar el post como eliminado: {str(e)}"
        )
    
# ================================================================================
# SECCIÓN: NUEVOS ENDPOINTS PARA GESTIÓN DE IMÁGENES DE PREVISUALIZACIÓN (WIP)
# Estos endpoints se añaden a tu router existente.
# ================================================================================

@router.post(
    "/{post_id}/generate-preview-image",
    response_model=GeneratePreviewImageResponse,
    summary="Generar Imagen de Previsualización con IA para WIP",
    description="Genera una imagen usando IA basada en el contenido del post o un prompt customizado. "
                "Limpia la carpeta 'wip' del post y guarda la nueva imagen allí.",
    tags=["Posts - Image Management"] # Nueva tag para agrupar
)
async def generate_ia_preview_image_for_wip(
    request_data: GeneratePreviewImageRequest, 
    post_id: UUID = Path(..., description="ID del post para el cual generar la preview."),
    *, 
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    start_time_total = datetime.now()
    logger.info(f"TIMING - [{start_time_total.isoformat()}] - INICIO generate_ia_preview_image_for_wip para post {post_id}, user {current_user.user_id}")

    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")

    # 1. Obtener el post para verificar pertenencia y obtener contenido para prompt si es necesario
    start_time_db_fetch = datetime.now()
    try:
        # SIN await para la llamada a DB (asumiendo comportamiento síncrono observado)
        post_query_response = supabase.table("posts").select("id, title, content_text, organization_id").eq("id", str(post_id)).eq("organization_id", str(current_user.organization_id)).limit(1).execute()
        
        time_taken_db_fetch = datetime.now() - start_time_db_fetch
        logger.info(f"TIMING - DB fetch para post {post_id} tomó: {time_taken_db_fetch.total_seconds():.4f}s")

        if not post_query_response.data:
            logger.warning(f"Post {post_id} no encontrado o no pertenece a org {current_user.organization_id} para generar preview.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post con ID {post_id} no encontrado o no pertenece a la organización.")
        post_db_data = post_query_response.data[0]
    except APIError as e:
        time_taken_db_fetch_error = datetime.now() - start_time_db_fetch
        logger.error(f"TIMING - DB Error obteniendo post {post_id} ({time_taken_db_fetch_error.total_seconds():.4f}s): {e.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al acceder a datos del post.")
    
    # 2. Determinar el prompt para la IA
    prompt_text = request_data.custom_prompt
    if not prompt_text: 
        prompt_text_title = post_db_data.get("title", "")
        prompt_text_content = post_db_data.get("content_text", "")[:200] # Primeros 200 chars
        
        if prompt_text_title and len(prompt_text_title.strip()) >= 5:
            prompt_text = f"Una imagen para un post titulado: '{prompt_text_title}'. Contenido adicional: '{prompt_text_content}'"
        elif prompt_text_content and len(prompt_text_content.strip()) >= 10:
            prompt_text = f"Una imagen relacionada con el siguiente contenido: '{prompt_text_content}'"
        else:
            logger.warning(f"No se pudo generar prompt para post {post_id}. Título: '{prompt_text_title}', Contenido (extracto): '{prompt_text_content}'")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo generar un prompt adecuado desde el post. Proporcione un prompt customizado o más contenido en el post.")
    
    logger.info(f"Generando imagen IA para WIP (post {post_id}) con prompt: '{prompt_text[:100]}...'")

    # 3. Limpiar la carpeta /wip/ del post ANTES de generar la nueva imagen
    start_time_wip_cleanup = datetime.now()
    wip_folder_path = storage_service.get_wip_folder_path(current_user.organization_id, post_id)
    cleanup_success, cleanup_error = await storage_service.delete_all_files_in_folder(
        supabase_client=supabase, bucket_name=storage_service.POST_PREVIEWS_BUCKET, folder_path=wip_folder_path
    )
    time_taken_wip_cleanup = datetime.now() - start_time_wip_cleanup
    logger.info(f"TIMING - Limpieza de WIP para post {post_id} ({wip_folder_path}) tomó: {time_taken_wip_cleanup.total_seconds():.4f}s. Éxito: {cleanup_success}")

    if not cleanup_success:
        # Loguear el error pero continuar; la subida a WIP usará upsert y sobrescribirá.
        logger.warning(f"Fallo al limpiar WIP para post {post_id} antes de generar preview IA: {cleanup_error}")

    # 4. Llamar al servicio de IA para generar y subir la imagen a WIP
    start_time_ai_service = datetime.now()
    public_url, storage_path, extension, content_type, ai_upload_error = await ai_image_generator.generate_and_upload_ai_image_to_wip(
        prompt_text=prompt_text, 
        organization_id=current_user.organization_id,
        post_id=post_id, 
        supabase_client=supabase
    )
    time_taken_ai_service = datetime.now() - start_time_ai_service
    logger.info(f"TIMING - Servicio ai_image_generator.generate_and_upload_ai_image_to_wip para post {post_id} tomó: {time_taken_ai_service.total_seconds():.4f}s")

    if ai_upload_error or not all([public_url, storage_path, extension, content_type]):
        logger.error(f"Error en generate_and_upload_ai_image_to_wip para post {post_id}: {ai_upload_error}")
        status_code_err = status.HTTP_502_BAD_GATEWAY
        if ai_upload_error and ("bloqueado" in ai_upload_error.lower() or "política de contenido" in ai_upload_error.lower()):
            status_code_err = status.HTTP_400_BAD_REQUEST
        
        time_taken_total_error = datetime.now() - start_time_total
        logger.info(f"TIMING - [{datetime.now().isoformat()}] - ERROR en generate_ia_preview_image_for_wip para post {post_id}. Total: {time_taken_total_error.total_seconds():.4f}s")
        raise HTTPException(status_code=status_code_err, detail=f"Error al generar o guardar imagen de previsualización: {ai_upload_error or 'Datos de imagen inválidos.'}")

    response_payload = GeneratePreviewImageResponse(
        preview_image_url=public_url, 
        preview_storage_path=storage_path,
        preview_image_extension=extension, 
        preview_content_type=content_type
    )
    
    time_taken_total_success = datetime.now() - start_time_total
    logger.info(f"TIMING - [{datetime.now().isoformat()}] - ÉXITO generate_ia_preview_image_for_wip para post {post_id}. Total: {time_taken_total_success.total_seconds():.4f}s. URL: {public_url}")
    
    return response_payload

# ================================================================================
# SECCIÓN: MODIFICACIÓN DEL ENDPOINT PATCH PARA MANEJO DE IMÁGENES
# ================================================================================
@router.patch(
    "/{post_id}", 
    response_model=PostResponse,
    summary="Actualizar Parcialmente un Post (con manejo de imágenes)",
    description="Actualiza campos de un post. Permite confirmar una imagen de 'wip' como principal, "
                "borrar la imagen principal actual, o solo actualizar textos (descartando cualquier imagen en 'wip').",
    tags=["Posts"]
)
async def update_post_partial(
    post_id: UUID = Path(..., description="El ID del post a actualizar"),
    *, 
    post_update_data: PostUpdate, 
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
        # --- VALIDACIÓN MANUAL AÑADIDA ---
    # Solo validamos si el campo fue enviado en el payload del PATCH
    if post_update_data.content_type is not None:
        try:
            ContentTypeEnum[post_update_data.content_type]
        except KeyError:
            valid_options = [e.name for e in ContentTypeEnum]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Valor inválido para 'content_type'. Las opciones válidas son: {valid_options}"
            )
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!!! ESTOY EJECUTANDO ESTA VERSIÓN DEL PATCH !!!!")
    print(f"!!!! Payload recibido aquí: {post_update_data.model_dump_json(indent=2)}")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    request_start_time = datetime.now()
    logger.info(f"PATCH_LOG [{request_start_time.isoformat()}] - INICIO para post {post_id}, user {current_user.user_id}")
    logger.debug(f"PATCH_LOG - Payload recibido (post_update_data): {post_update_data.model_dump_json(indent=2)}")

    if not current_user.organization_id:
        logger.warning(f"PATCH_LOG - Usuario {current_user.user_id} sin organization_id intentando actualizar post {post_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")

    # Validación de payload
    has_confirm_wip = post_update_data.confirm_wip_image_details is not None
    # Verificar si se envió explícitamente `media_url: null` (o `media_storage_path: null`)
    # `post_update_data.model_fields_set` contiene los nombres de los campos que el cliente envió.
    is_deleting_media_explicitly = (
        'media_url' in post_update_data.model_fields_set and post_update_data.media_url is None
    ) or (
        'media_storage_path' in post_update_data.model_fields_set and post_update_data.media_storage_path is None
    )
    is_setting_new_media_directly = (
        ('media_url' in post_update_data.model_fields_set and post_update_data.media_url is not None) or
        ('media_storage_path' in post_update_data.model_fields_set and post_update_data.media_storage_path is not None)
    ) and not is_deleting_media_explicitly

    logger.debug(f"PATCH_LOG - Flags de imagen: has_confirm_wip={has_confirm_wip}, is_deleting_media_explicitly={is_deleting_media_explicitly}, is_setting_new_media_directly={is_setting_new_media_directly}")

    if has_confirm_wip and (is_deleting_media_explicitly or is_setting_new_media_directly):
        logger.warning(f"PATCH_LOG - Conflicto de payload para post {post_id}: Se intentó confirmar WIP y borrar/setear media principal.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede confirmar una imagen de previsualización y simultáneamente borrar o establecer una nueva imagen principal directamente."
        )

    # 1. Obtener el post actual de la DB
    logger.debug(f"PATCH_LOG - Obteniendo post actual {post_id} de la DB.")
    try:
        # SIN await (asumiendo comportamiento síncrono de .execute() en tu entorno)
        current_post_res = supabase.table("posts").select("*").eq("id", str(post_id)).eq("organization_id", str(current_user.organization_id)).is_("deleted_at", None).limit(1).execute()
        if not current_post_res.data:
            logger.warning(f"PATCH_LOG - Post {post_id} no encontrado o no pertenece a org {current_user.organization_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado o no pertenece a la organización.")
        current_post_db_data = current_post_res.data[0]
        logger.debug(f"PATCH_LOG - Post actual obtenido: {current_post_db_data.get('id')}, media_url actual: {current_post_db_data.get('media_url')}")
    except APIError as e:
        logger.error(f"PATCH_LOG - DB Error obteniendo post {post_id}: {e.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener datos del post para actualizar.")
    
    old_media_storage_path = current_post_db_data.get("media_storage_path")
    logger.debug(f"PATCH_LOG - Old media_storage_path: {old_media_storage_path}")

    # Preparar payload para actualizar DB
    raw_payload_from_client = post_update_data.model_dump(exclude_unset=True, exclude_none=False)
    
    db_update_payload: Dict[str, any] = {}

    # Iterar sobre los campos enviados por el cliente y construir el payload para la DB
    for key, value in raw_payload_from_client.items():
        if key == "confirm_wip_image_details":
            # Ignoramos este campo, no va a la DB
            continue
        
        if isinstance(value, UUID):
            # Convertimos UUID a string
            db_update_payload[key] = str(value)
        elif isinstance(value, datetime):
            # Convertimos datetime a string en formato ISO 8601 con zona horaria
            db_update_payload[key] = value.isoformat()
        elif isinstance(value, HttpUrl):
            # Convertimos HttpUrl a string
            db_update_payload[key] = str(value)
        else:
            # Para todos los demás tipos (str, int, bool, None), los pasamos tal cual
            db_update_payload[key] = value

    logger.debug(f"PATCH_LOG - Payload inicial para DB (después de model_dump y conversión de HttpUrl): {db_update_payload}")
    if 'confirm_wip_image_details' in db_update_payload: # Este campo no va a la DB
        del db_update_payload['confirm_wip_image_details']
    
    final_storage_paths_to_delete_post_db: List[Tuple[str, str]] = [] # (bucket_name, path_in_bucket)
    wip_folder_path = storage_service.get_wip_folder_path(current_user.organization_id, post_id)
    moved_wip_image_final_path: Optional[str] = None # Para rollback si DB falla

    # --- Lógica de Imágenes ---
    if has_confirm_wip: 
        wip_details = post_update_data.confirm_wip_image_details
        logger.info(f"PATCH_LOG - Confirmando imagen WIP para post {post_id}: path='{wip_details.path}', ext='{wip_details.extension}', type='{wip_details.content_type}'")

        expected_wip_storage_path = storage_service.get_wip_image_storage_path(current_user.organization_id, post_id, wip_details.extension)
        if wip_details.path != expected_wip_storage_path:
            logger.error(f"PATCH_LOG - Path de WIP proporcionado '{wip_details.path}' no coincide con esperado '{expected_wip_storage_path}'.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El path de la imagen de previsualización a confirmar es incorrecto.")

        unique_final_filename = f"{uuid_pkg.uuid4()}.{wip_details.extension}"
        destination_final_media_path = storage_service.get_post_media_storage_path(current_user.organization_id, post_id, unique_final_filename)
        logger.debug(f"PATCH_LOG - Destino final en post_media: {destination_final_media_path}")

        move_start_time = datetime.now()
        moved_path, move_error = await storage_service.move_file_in_storage( # moved_path se define aquí
            supabase_client=supabase,
            source_bucket=storage_service.POST_PREVIEWS_BUCKET,
            source_path_in_bucket=wip_details.path,
            destination_bucket=storage_service.POST_MEDIA_BUCKET,
            destination_path_in_bucket=destination_final_media_path,
            content_type_for_destination=wip_details.content_type
        )
        move_time_taken = (datetime.now() - move_start_time).total_seconds()
        logger.info(f"PATCH_LOG - storage_service.move_file_in_storage tomó: {move_time_taken:.4f}s. Resultado: moved_path='{moved_path}', move_error='{move_error}'")

        if move_error or not moved_path: # Verificar error ANTES de usar moved_path
            logger.error(f"PATCH_LOG - Error moviendo imagen de WIP a Media para post {post_id}: {move_error}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo confirmar la imagen de previsualización (error de storage): {move_error}")
        
        # --- MOVER ESTAS LÍNEAS AQUÍ ---
        moved_wip_image_final_path = moved_path # Para posible rollback
        
        new_media_url = storage_service._build_public_url(supabase, storage_service.POST_MEDIA_BUCKET, moved_path, add_timestamp_bust=False)
        db_update_payload["media_url"] = str(new_media_url) 
        db_update_payload["media_storage_path"] = moved_path # Ahora moved_path tiene un valor
        # --- FIN DE LÍNEAS MOVIDAS ---
        
        logger.info(f"PATCH_LOG - Payload de DB actualizado con nueva media: media_url='{db_update_payload['media_url']}', media_storage_path='{db_update_payload['media_storage_path']}'")

        if old_media_storage_path and old_media_storage_path != moved_path:
            logger.info(f"PATCH_LOG - Programando borrado de imagen principal antigua: {storage_service.POST_MEDIA_BUCKET}/{old_media_storage_path}")
            final_storage_paths_to_delete_post_db.append((storage_service.POST_MEDIA_BUCKET, old_media_storage_path))
        
        elif is_deleting_media_explicitly: # Borrar imagen principal
         logger.info(f"PATCH_LOG - Solicitud para borrar imagen principal del post {post_id}.")
         db_update_payload["media_url"] = None
         db_update_payload["media_storage_path"] = None
        if old_media_storage_path:
            logger.info(f"PATCH_LOG - Programando borrado de imagen principal existente: {storage_service.POST_MEDIA_BUCKET}/{old_media_storage_path}")
            final_storage_paths_to_delete_post_db.append((storage_service.POST_MEDIA_BUCKET, old_media_storage_path))
    
    # --- Actualizar Base de Datos ---
    updated_post_from_db = None # Inicializar
    # Solo actualizar si hay algo que cambiar en el payload de la DB.
    # db_update_payload ya no contendrá 'confirm_wip_image_details'.
    # Si solo se envió 'confirm_wip_image_details' y ningún otro campo, db_update_payload
    # contendrá 'media_url' y 'media_storage_path'.
    if db_update_payload or (has_confirm_wip and not db_update_payload.get("media_url")): # El segundo caso es para forzar update si solo se confirmó WIP
        # La condición `has_confirm_wip and not db_update_payload.get("media_url")` es un poco extraña,
        # ya que si `has_confirm_wip` es true, `media_url` DEBERÍA estar en `db_update_payload`.
        # Más simple: si `db_update_payload` tiene algo (textos O nuevos media_url/path), actualiza.
        # Si solo se envió `confirm_wip_image_details` y no otros campos, `db_update_payload` solo tendrá
        # `media_url` y `media_storage_path`.
        
        # Si no hay cambios de texto Y no hay operación de imagen (confirmar o borrar),
        # `db_update_payload` podría estar vacío aquí (si solo se envió un payload de PATCH vacío).
        # Si `post_update_data` estaba vacío (sin campos de texto, sin confirm_wip, sin media_url:null),
        # entonces `db_update_payload` estará vacío. En ese caso, solo limpiamos WIP si no se confirmó.
        
        if not db_update_payload: # Caso: payload de PATCH estaba vacío.
            logger.info(f"PATCH_LOG - Payload de DB está vacío para post {post_id}. No se actualiza DB. Solo se limpiará WIP si no se confirmó.")
            updated_post_from_db = current_post_db_data
        else:
            logger.info(f"PATCH_LOG - Actualizando post {post_id} en DB con payload: {db_update_payload}")
            db_update_start_time = datetime.now()
            try:
                # SIN await para la llamada a DB
                update_res = supabase.table("posts").update(db_update_payload).eq("id", str(post_id)).execute()
                db_update_time_taken = (datetime.now() - db_update_start_time).total_seconds()

                if not update_res.data or len(update_res.data) == 0:
                    logger.error(f"PATCH_LOG - Fallo al actualizar post {post_id} en DB (no se devolvieron datos). Tiempo: {db_update_time_taken:.4f}s. Respuesta: {update_res}")
                    # Podría ser que el post fue eliminado mientras tanto o RLS lo impidió.
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El post no pudo ser actualizado (no encontrado o sin cambios).")
                updated_post_from_db = update_res.data[0]
                logger.info(f"PATCH_LOG - Post {post_id} actualizado exitosamente en DB. Tiempo: {db_update_time_taken:.4f}s")

            except APIError as e_db_update:
                db_update_time_taken_error = (datetime.now() - db_update_start_time).total_seconds()
                logger.error(f"PATCH_LOG - DB Error actualizando post {post_id}: {e_db_update.message}. Tiempo: {db_update_time_taken_error:.4f}s", exc_info=True)
                if moved_wip_image_final_path:
                    logger.warning(f"PATCH_LOG - DB update falló para post {post_id}. Intentando rollback de storage: Borrar {moved_wip_image_final_path} de {storage_service.POST_MEDIA_BUCKET}")
                    rollback_start_time = datetime.now()
                    await storage_service.delete_files_from_storage(supabase, storage_service.POST_MEDIA_BUCKET, [moved_wip_image_final_path])
                    rollback_time_taken = (datetime.now() - rollback_start_time).total_seconds()
                    logger.info(f"PATCH_LOG - Rollback de storage tomó: {rollback_time_taken:.4f}s")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al guardar cambios en el post: {e_db_update.message}")
    else: # No hubo payload para la DB (ej. PATCH vacío y sin confirm_wip o media_url:null)
        logger.info(f"PATCH_LOG - No hay payload para actualizar DB para post {post_id}. Se usará el post actual para la respuesta. Solo se limpiará WIP si aplica.")
        updated_post_from_db = current_post_db_data


    # --- Ejecutar Limpieza de Storage Post-Actualización Exitosa de DB ---
    if final_storage_paths_to_delete_post_db:
        logger.info(f"PATCH_LOG - Ejecutando borrados programados de storage para post {post_id}: {final_storage_paths_to_delete_post_db}")
        for bucket, path_to_delete in final_storage_paths_to_delete_post_db:
            delete_start_time = datetime.now()
            delete_results = await storage_service.delete_files_from_storage(supabase, bucket, [path_to_delete])
            delete_time_taken = (datetime.now() - delete_start_time).total_seconds()
            for _path, success, err_msg in delete_results:
                if not success:
                    logger.error(f"PATCH_LOG - Fallo en limpieza de storage post-DB: No se pudo borrar {bucket}/{_path}. Error: {err_msg}. Tiempo: {delete_time_taken:.4f}s")
                else:
                    logger.info(f"PATCH_LOG - Limpieza de storage exitosa: {bucket}/{_path} borrado. Tiempo: {delete_time_taken:.4f}s")
    
    # Limpiar la carpeta WIP si NO se confirmó una imagen desde ella
    if not has_confirm_wip: # Si no se usaron detalles de confirm_wip
        logger.info(f"PATCH_LOG - Limpiando carpeta WIP para post {post_id} ya que no se confirmó ninguna imagen de allí (o se borró la principal). Path: {wip_folder_path}")
        wip_cleanup_start_time = datetime.now()
        _success_wip, _err_wip = await storage_service.delete_all_files_in_folder(
            supabase_client=supabase, bucket_name=storage_service.POST_PREVIEWS_BUCKET, folder_path=wip_folder_path
        )
        wip_cleanup_time_taken = (datetime.now() - wip_cleanup_start_time).total_seconds()
        if not _success_wip:
            logger.error(f"PATCH_LOG - Fallo al limpiar carpeta WIP {wip_folder_path} para post {post_id} después de actualizar post: {_err_wip}. Tiempo: {wip_cleanup_time_taken:.4f}s")
        else:
            logger.info(f"PATCH_LOG - Limpieza de carpeta WIP {wip_folder_path} exitosa. Tiempo: {wip_cleanup_time_taken:.4f}s")

    total_request_time = (datetime.now() - request_start_time).total_seconds()
    logger.info(f"PATCH_LOG [{datetime.now().isoformat()}] - FIN para post {post_id}. Tiempo total: {total_request_time:.4f}s")
    
    # Devolver el post con los datos actualizados
    # `updated_post_from_db` debe ser el dict del post de la DB
    if not updated_post_from_db: # Fallback muy improbable
        logger.error(f"PATCH_LOG - updated_post_from_db es None al final del PATCH para post {post_id}. Esto no debería ocurrir.")
        # Re-fetch como último recurso, aunque indica un error lógico previo.
        final_fallback_res = supabase.table("posts").select("*").eq("id", str(post_id)).limit(1).execute()
        if final_fallback_res.data:
            updated_post_from_db = final_fallback_res.data[0]
        else: # El post realmente no existe o no es accesible
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El post no pudo ser recuperado después de la actualización.")

    return PostResponse.model_validate(updated_post_from_db)



# ================================================================================
# Endpoint SOFT DELETE - Considerar limpieza de imágenes aquí
# ================================================================================
@router.delete(
    "/{post_id}",
    response_model=PostResponse, # O un modelo simple de éxito/confirmación
    summary="Borrar Lógicamente un Post (y limpiar sus imágenes)",
    tags=["Posts"]
    # ... (resto de tu decoración de endpoint)
)
async def soft_delete_post(
    post_id: UUID = Path(..., description="El ID del post a marcar como eliminado"),
    *, # <--- MARCADOR (Buena práctica añadirlo aquí también)
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")
    try:
        # SIN await
        post_to_delete_res = supabase.table("posts").select("id, organization_id, media_storage_path").eq("id", str(post_id)).eq("organization_id", str(current_user.organization_id)).is_("deleted_at", None).limit(1).execute()
        if not post_to_delete_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado para eliminar.")
        post_data_for_delete = post_to_delete_res.data[0]
    except APIError as e:
        # ...
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error obteniendo post para eliminar.")
    
    org_id_of_post = UUID(post_data_for_delete["organization_id"])
    media_storage_path_to_delete = post_data_for_delete.get("media_storage_path")
    
    now_utc = datetime.now(pytz.utc)
    update_payload = { "deleted_at": now_utc.isoformat(), "status": "deleted" }
    try:
        # SIN await
        delete_update_res = supabase.table("posts").update(update_payload).eq("id", str(post_id)).execute()
        if not delete_update_res.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al marcar post como eliminado.")
        deleted_post_data = delete_update_res.data[0]
    except APIError as e_db_delete:
        # ...
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de DB al eliminar: {e_db_delete.message}")

    # --- Limpieza de Imágenes (las llamadas a storage_service SÍ usan await) ---
    if media_storage_path_to_delete:
        # CON await
        delete_main_results = await storage_service.delete_files_from_storage(
            supabase, storage_service.POST_MEDIA_BUCKET, [media_storage_path_to_delete]
        )
        # ... (loguear errores)

    wip_folder_to_delete = storage_service.get_wip_folder_path(org_id_of_post, post_id)
    # CON await
    _success_wip_del, _err_wip_del = await storage_service.delete_all_files_in_folder(
        supabase, storage_service.POST_PREVIEWS_BUCKET, wip_folder_to_delete
    )
    # ... (loguear errores)

    return PostResponse.model_validate(deleted_post_data)



## ================================================================================
## NUEVO ENDPOINT PARA SUBIDA DE IMAGEN DE PREVISUALIZACIÓN DE USUARIO A WIP
## ================================================================================

@router.post(
    "/{post_id}/upload-wip-preview",
    response_model=GeneratePreviewImageResponse, # Reutilizamos el mismo modelo de respuesta que para la IA
    summary="Subir Imagen de Previsualización de Usuario a WIP",
    description="El usuario sube un archivo de imagen, el backend limpia la carpeta 'wip' del post "
                "y sube la nueva imagen allí. Devuelve los detalles de la imagen en WIP.",
    tags=["Posts - Image Management"]
)
async def upload_user_preview_image_to_wip(
    post_id: UUID = Path(..., description="ID del post para el cual subir la previsualización."),
    image_file: UploadFile = File(..., description="El archivo de imagen a subir."), # FastAPI maneja el multipart/form-data
    *,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    request_start_time = datetime.now()
    logger.info(f"UPLOAD_WIP_LOG [{request_start_time.isoformat()}] - INICIO para post {post_id}, user {current_user.user_id}, filename: {image_file.filename}")

    if not current_user.organization_id:
        logger.warning(f"UPLOAD_WIP_LOG - Usuario {current_user.user_id} sin organization_id intentando subir preview para post {post_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")

    # 1. Validaciones Opcionales del Archivo (Tipo, Tamaño)
    # Estos límites deberían idealmente estar en la configuración (settings)
    ALLOWED_CONTENT_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"]
    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024 # 20 MB

    if image_file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"UPLOAD_WIP_LOG - Tipo de archivo no permitido: {image_file.content_type} para post {post_id}. Archivo: {image_file.filename}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo de archivo no permitido: {image_file.content_type}. Permitidos: png, jpg, jpeg, webp, gif.")
    
    # Para verificar el tamaño, necesitamos leer el archivo, lo cual puede ser costoso para archivos grandes.
    # FastAPI/Starlette pueden tener un límite máximo de tamaño de cuerpo de solicitud configurable.
    # Si el archivo es muy grande, podría fallar antes de llegar aquí.
    # Una forma de verificar el tamaño si UploadFile lo soporta sin leer todo en memoria:
    # if image_file.size and image_file.size > MAX_FILE_SIZE_BYTES:
    # logger.warning(f"UPLOAD_WIP_LOG - Archivo demasiado grande: {image_file.size} bytes para post {post_id}. Archivo: {image_file.filename}")
    # raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.")

    # 2. Verificar que el post pertenece al usuario/organización (seguridad)
    logger.debug(f"UPLOAD_WIP_LOG - Verificando post {post_id} para org {current_user.organization_id}.")
    try:
        # SIN await (asumiendo comportamiento síncrono de .execute())
        post_check_res = supabase.table("posts").select("id").eq("id", str(post_id)).eq("organization_id", str(current_user.organization_id)).limit(1).execute()
        if not post_check_res.data:
            logger.warning(f"UPLOAD_WIP_LOG - Post {post_id} no encontrado o no pertenece a org {current_user.organization_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post con ID {post_id} no encontrado o no pertenece a la organización.")
    except APIError as e:
        logger.error(f"UPLOAD_WIP_LOG - DB Error verificando post {post_id}: {e.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al verificar datos del post.")

    # 3. Limpiar la carpeta /wip/ del post ANTES de subir la nueva imagen
    wip_folder_path = storage_service.get_wip_folder_path(current_user.organization_id, post_id)
    logger.info(f"UPLOAD_WIP_LOG - Limpiando carpeta WIP: {wip_folder_path} para post {post_id}")
    
    cleanup_start_time = datetime.now()
    cleanup_success, cleanup_error = await storage_service.delete_all_files_in_folder(
        supabase_client=supabase, # Este cliente usa service_key implícitamente
        bucket_name=storage_service.POST_PREVIEWS_BUCKET,
        folder_path=wip_folder_path
    )
    cleanup_time_taken = (datetime.now() - cleanup_start_time).total_seconds()
    logger.info(f"UPLOAD_WIP_LOG - Limpieza de WIP para post {post_id} tomó: {cleanup_time_taken:.4f}s. Éxito: {cleanup_success}")

    if not cleanup_success:
        logger.error(f"UPLOAD_WIP_LOG - Fallo crítico al limpiar carpeta WIP '{wip_folder_path}' para post {post_id}: {cleanup_error}")
        # Decidimos fallar aquí si la limpieza no es exitosa, para evitar estados inconsistentes en WIP.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error preparando el espacio para la nueva previsualización: {cleanup_error}")

    # 4. Preparar datos para la subida
    try:
        file_bytes = await image_file.read() # Leer el contenido del archivo
        # `image_file.filename` puede ser None si no se envía, o podría no tener extensión.
        original_filename = image_file.filename if image_file.filename else "untitled"
        file_extension = original_filename.split(".")[-1].lower() if "." in original_filename else "png" # Default a png
        
        # Re-validar extensión por si el content_type era genérico
        valid_extensions = ["png", "jpg", "jpeg", "webp", "gif"]
        if file_extension not in valid_extensions:
            # Si el content_type pasó pero la extensión inferida no es válida, usar una default o la del content_type
            if image_file.content_type == "image/png": file_extension = "png"
            elif image_file.content_type == "image/jpeg": file_extension = "jpg"
            elif image_file.content_type == "image/webp": file_extension = "webp"
            elif image_file.content_type == "image/gif": file_extension = "gif"
            else: # Último recurso, pero el chequeo de content_type debería haberlo prevenido
                logger.warning(f"UPLOAD_WIP_LOG - Extensión de archivo '{file_extension}' no es la esperada para post {post_id}, pero content_type '{image_file.content_type}' fue permitido. Se usará extensión inferida o 'png'.")
                if file_extension not in valid_extensions: file_extension = "png" # Default final


        content_type = image_file.content_type or f"image/{file_extension}" # Usar el content_type del archivo
        if not content_type.startswith("image/"): # Doble chequeo
            logger.error(f"UPLOAD_WIP_LOG - Content-type final '{content_type}' no es de imagen para post {post_id}.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo proporcionado no parece ser una imagen válida después del procesamiento.")

    except Exception as e_read:
        logger.error(f"UPLOAD_WIP_LOG - Error leyendo el archivo subido para post {post_id}: {e_read}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo procesar el archivo subido.")

    active_wip_storage_path = storage_service.get_wip_image_storage_path(
        organization_id=current_user.organization_id,
        post_id=post_id,
        extension=file_extension # Usar la extensión determinada
    )
    
    logger.info(f"UPLOAD_WIP_LOG - Subiendo archivo '{original_filename}' (como '{active_wip_storage_path}') a WIP para post {post_id}. Content-type: '{content_type}', Bytes: {len(file_bytes)}")
    
    upload_start_time = datetime.now()
    # 5. Subir el archivo a WIP usando el storage_service
    public_url, uploaded_path, upload_error = await storage_service.upload_file_bytes_to_storage(
        supabase_client=supabase,
        bucket_name=storage_service.POST_PREVIEWS_BUCKET,
        file_path_in_bucket=active_wip_storage_path,
        file_bytes=file_bytes,
        content_type=content_type, # Content type del archivo
        upsert=True, # Sobrescribe preview_active.{ext} si ya existe con esa extensión
        add_timestamp_to_url=True # Cache-busting para la URL de preview
    )
    upload_time_taken = (datetime.now() - upload_start_time).total_seconds()
    logger.info(f"UPLOAD_WIP_LOG - Subida a WIP para post {post_id} tomó: {upload_time_taken:.4f}s. URL: {public_url}, Error: {upload_error}")

    if upload_error or not public_url or not uploaded_path:
        logger.error(f"UPLOAD_WIP_LOG - Error subiendo archivo de usuario a WIP para post {post_id}: {upload_error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al guardar la imagen de previsualización: {upload_error}")

    response_payload = GeneratePreviewImageResponse(
        preview_image_url=public_url,
        preview_storage_path=uploaded_path,
        preview_image_extension=file_extension,
        preview_content_type=content_type
    )
    
    total_request_time = (datetime.now() - request_start_time).total_seconds()
    logger.info(f"UPLOAD_WIP_LOG [{datetime.now().isoformat()}] - ÉXITO para post {post_id}. Tiempo total: {total_request_time:.4f}s.")
    
    return response_payload
