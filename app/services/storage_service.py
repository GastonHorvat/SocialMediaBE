# app/services/storage_service.py
import logging
import time
import asyncio
import uuid # Para generar nombres de archivo únicos para post_media
from typing import List, Tuple, Optional, Dict # Asegúrate que Dict esté importado
from uuid import UUID as PyUUID

from supabase import Client as SupabaseClient
# from supabase.lib.client_options import ClientOptions # No es estrictamente necesario para tipado aquí
# from supabase.lib.storage.storage_file_api import Bucket # No es estrictamente necesario para tipado aquí

# --- Constantes de Buckets ---
POST_MEDIA_BUCKET = "content.flow.media"
POST_PREVIEWS_BUCKET = "post.previews"
WIP_FOLDER_NAME = "wip"
WIP_ACTIVE_FILENAME_BASE = "preview_active"

logger = logging.getLogger(__name__)

# --- Funciones de Construcción de Rutas (Helpers) ---
# (Estas funciones son iguales a las del mensaje anterior, las omito aquí por brevedad
# pero deben estar presentes en el archivo final)

def get_post_media_storage_path(organization_id: PyUUID, post_id: PyUUID, final_filename_with_extension: str) -> str:
    return f"{str(organization_id)}/posts/{str(post_id)}/images/{final_filename_with_extension}"

def get_wip_folder_path(organization_id: PyUUID, post_id: PyUUID) -> str:
    return f"{str(organization_id)}/posts/{str(post_id)}/{WIP_FOLDER_NAME}/"

def get_wip_image_storage_path(organization_id: PyUUID, post_id: PyUUID, extension: str) -> str:
    clean_extension = extension.lstrip('.')
    wip_folder = get_wip_folder_path(organization_id, post_id)
    return f"{wip_folder}{WIP_ACTIVE_FILENAME_BASE}.{clean_extension}"

# --- Funciones de Interacción con Storage (Async con Supabase-py v2.x) ---

def _build_public_url(supabase_client: SupabaseClient, bucket_name: str, file_path_in_bucket: str, add_timestamp_bust: bool = False) -> str:
    public_url = supabase_client.storage.from_(bucket_name).get_public_url(file_path_in_bucket)
    if add_timestamp_bust:
        timestamp = int(time.time())
        public_url = f"{public_url}?v={timestamp}"
    return public_url

async def upload_file_bytes_to_storage(
    supabase_client: SupabaseClient,
    bucket_name: str,
    file_path_in_bucket: str,
    file_bytes: bytes,
    content_type: str,
    upsert: bool = True,
    add_timestamp_to_url: bool = False
) -> Tuple[Optional[str], Optional[str], Optional[str]]: # (public_url, storage_path, error_message)
    try:
        # --- CORRECCIÓN: Envolver la llamada síncrona .upload() en asyncio.to_thread ---
        def _upload_sync():
            # Esta función se ejecutará en un hilo separado
            # .upload() en supabase-py 2.x devuelve un objeto UploadResponse o similar,
            # o lanza una excepción en caso de error HTTP.
            response_data = supabase_client.storage.from_(bucket_name).upload(
                path=file_path_in_bucket,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": str(upsert).lower()},
            )
            # Aquí podrías inspeccionar response_data si fuera necesario, pero
            # si hay un error HTTP (4xx, 5xx), .upload() debería lanzar una excepción
            # que será capturada por el bloque try...except externo.
            return response_data # O simplemente no devolver nada si solo nos importa la excepción

        await asyncio.to_thread(_upload_sync)
        # Si _upload_sync no lanzó una excepción, la subida fue aceptada por el servidor.
        # --- FIN DE LA CORRECCIÓN ---
        
        public_url = _build_public_url(supabase_client, bucket_name, file_path_in_bucket, add_timestamp_bust=add_timestamp_to_url)
        
        logger.info(f"Archivo subido a {bucket_name}/{file_path_in_bucket}. URL: {public_url}")
        return public_url, file_path_in_bucket, None

    except Exception as e:
        # El SDK de Supabase puede lanzar errores específicos (ej. StorageApiError si RLS falla,
        # o errores de la librería httpx si la conexión falla).
        logger.error(f"Error al subir a Supabase Storage (bucket: {bucket_name}, path: {file_path_in_bucket}): {type(e).__name__} - {e}", exc_info=True)
        # Devolver el mensaje de error de la excepción
        return None, None, str(e)

async def move_file_in_storage(
    supabase_client: SupabaseClient,
    source_bucket: str,
    source_path_in_bucket: str,
    destination_bucket: str,
    destination_path_in_bucket: str,
    content_type_for_destination: str # Añadido según discusión
) -> Tuple[Optional[str], Optional[str]]: # (final_destination_path, error_message)
    try:
        if source_bucket == destination_bucket:
            # supabase-py v2.x.x .move() es async
            # Mueve DENTRO del mismo bucket
            await supabase_client.storage.from_(source_bucket).move(
                from_path=source_path_in_bucket,
                to_path=destination_path_in_bucket
            )
            logger.info(f"Archivo movido de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket} (mismo bucket).")
            # Para move dentro del mismo bucket, el archivo fuente se elimina automáticamente.
            return destination_path_in_bucket, None # El path de destino es el final
        else:
            # Mover entre buckets: Descargar + Subir + Borrar Fuente
            
            # Paso 1: Descargar
            # supabase-py v2.x.x .download() es async
            file_bytes_to_move: bytes = await supabase_client.storage.from_(source_bucket).download(path=source_path_in_bucket)
            
            # En supabase-py v2, un error en download lanza una excepción (ej. StorageUnknownError si no existe)
            # en lugar de devolver un objeto de error.

            # Paso 2: Subir al nuevo bucket
            _public_url, _path, upload_error = await upload_file_bytes_to_storage(
                supabase_client,
                bucket_name=destination_bucket,
                file_path_in_bucket=destination_path_in_bucket,
                file_bytes=file_bytes_to_move,
                content_type=content_type_for_destination,
                upsert=True
            )
            if upload_error:
                err_msg = f"Fallo al subir a {destination_bucket}/{destination_path_in_bucket} después de descargar: {upload_error}"
                logger.error(err_msg)
                return None, err_msg # El archivo original sigue en source_bucket
            
            logger.info(f"Archivo 'movido' (descargado y subido) de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket}")

            # Paso 3: Borrar el archivo original de la fuente
            # supabase-py v2.x.x .remove() es async
            # No necesitamos un resultado detallado aquí, solo intentarlo.
            await delete_files_from_storage(supabase_client, source_bucket, [source_path_in_bucket])
            # La función delete_files_from_storage ya loguea el éxito/fallo del borrado.
            
            return destination_path_in_bucket, None

    except Exception as e:
        logger.error(f"Error moviendo archivo de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket}: {type(e).__name__} - {e}", exc_info=True)
        return None, f"Error de almacenamiento al mover archivo: {str(e)}"

async def delete_files_from_storage(
    supabase_client: SupabaseClient,
    bucket_name: str,
    list_of_file_paths: List[str]
) -> List[Tuple[str, bool, Optional[str]]]: # List of (path, success, error_message_if_any)
    if not list_of_file_paths:
        return []
    results = []
    for file_path in list_of_file_paths:
        try:
            # supabase-py v2.x.x .remove() es async
            # .remove() devuelve una lista de dicts con los resultados,
            # o lanza una excepción si hay un error más general.
            response_data_list = await supabase_client.storage.from_(bucket_name).remove(paths=[file_path])
            
            # Analizar la respuesta para este archivo específico
            # La respuesta es una lista, incluso si solo se borró un archivo.
            if response_data_list and isinstance(response_data_list, list) and len(response_data_list) > 0:
                item_result = response_data_list[0]
                if item_result.get("error"):
                    error_msg = f"{item_result.get('error')}: {item_result.get('message', 'Error desconocido')}"
                    logger.warning(f"Fallo al borrar {bucket_name}/{file_path}: {error_msg}")
                    results.append((file_path, False, error_msg))
                else:
                    logger.info(f"Archivo {bucket_name}/{file_path} borrado exitosamente.")
                    results.append((file_path, True, None))
            else: # Respuesta inesperada
                logger.warning(f"Respuesta inesperada al borrar {bucket_name}/{file_path}: {response_data_list}")
                results.append((file_path, False, "Respuesta inesperada del servicio de storage al borrar."))

        except Exception as e_single:
            logger.error(f"Excepción borrando archivo {bucket_name}/{file_path}: {type(e_single).__name__} - {e_single}", exc_info=True)
            results.append((file_path, False, str(e_single)))
    return results