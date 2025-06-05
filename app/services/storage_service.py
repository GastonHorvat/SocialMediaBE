# app/services/storage_service.py
import logging
import time
import asyncio
import uuid # Para generar nombres de archivo únicos para post_media
from typing import List, Tuple, Optional, Dict 
from uuid import UUID as PyUUID

from supabase import Client as SupabaseClient # Asumo que este es el cliente que estás usando

# --- Constantes de Buckets ---
POST_MEDIA_BUCKET = "content.flow.media" # Asumo que este es el bucket de medios finales
POST_PREVIEWS_BUCKET = "post.previews"   # Asumo que este es el bucket para WIP y previsualizaciones
WIP_FOLDER_NAME = "wip"
WIP_ACTIVE_FILENAME_BASE = "preview_active" # Usado para construir el nombre del archivo activo en WIP

logger = logging.getLogger(__name__)

# --- Funciones de Construcción de Rutas (Helpers) ---
# (Estas funciones son iguales a las del mensaje anterior, las omito aquí por brevedad
# pero deben estar presentes en el archivo final)

def get_post_media_storage_path(organization_id: PyUUID, post_id: PyUUID, final_filename_with_extension: str) -> str:
    return f"{str(organization_id)}/posts/{str(post_id)}/images/{final_filename_with_extension}"

def get_wip_folder_path(organization_id: PyUUID, post_id: PyUUID) -> str:
    # Asegúrate que el path de la carpeta termine con '/' para la función list() de Supabase
    # si esa es la convención que necesita para listar solo el contenido de esa carpeta.
    # Usualmente, para `list(path=folder_path)`, folder_path es un prefijo.
    return f"{str(organization_id)}/posts/{str(post_id)}/{WIP_FOLDER_NAME}" # Quitada la barra final para consistencia con list()

def get_wip_image_storage_path(organization_id: PyUUID, post_id: PyUUID, extension: str) -> str:
    clean_extension = extension.lstrip('.')
    # get_wip_folder_path ya no incluye la barra al final
    wip_folder_prefix = get_wip_folder_path(organization_id, post_id) 
    return f"{wip_folder_prefix}/{WIP_ACTIVE_FILENAME_BASE}.{clean_extension}"


# --- Funciones de Interacción con Storage ---

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
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        def _upload_sync():
            response_data = supabase_client.storage.from_(bucket_name).upload(
                path=file_path_in_bucket,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": str(upsert).lower()},
            )
            return response_data
        await asyncio.to_thread(_upload_sync)
        public_url = _build_public_url(supabase_client, bucket_name, file_path_in_bucket, add_timestamp_bust=add_timestamp_to_url)
        logger.info(f"Archivo subido a {bucket_name}/{file_path_in_bucket}. URL: {public_url}")
        return public_url, file_path_in_bucket, None
    except Exception as e:
        logger.error(f"Error al subir a Supabase Storage (bucket: {bucket_name}, path: {file_path_in_bucket}): {type(e).__name__} - {e}", exc_info=True)
        return None, None, str(e)

async def move_file_in_storage(
    supabase_client: SupabaseClient,
    source_bucket: str,
    source_path_in_bucket: str,
    destination_bucket: str,
    destination_path_in_bucket: str,
    content_type_for_destination: str
) -> Tuple[Optional[str], Optional[str]]:
    try:
        if source_bucket == destination_bucket:
            # Envolver llamada síncrona
            def _move_sync():
                return supabase_client.storage.from_(source_bucket).move(
                    from_path=source_path_in_bucket,
                    to_path=destination_path_in_bucket
                )
            await asyncio.to_thread(_move_sync)
            logger.info(f"Archivo movido de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket} (mismo bucket).")
            return destination_path_in_bucket, None
        else:
            # Descargar (síncrono envuelto)
            def _download_sync():
                return supabase_client.storage.from_(source_bucket).download(path=source_path_in_bucket)
            file_bytes_to_move: bytes = await asyncio.to_thread(_download_sync)
            
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
                return None, err_msg
            
            logger.info(f"Archivo 'movido' (descargado y subido) de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket}")
            await delete_files_from_storage(supabase_client, source_bucket, [source_path_in_bucket])
            return destination_path_in_bucket, None
    except Exception as e:
        logger.error(f"Error moviendo archivo de {source_bucket}/{source_path_in_bucket} a {destination_bucket}/{destination_path_in_bucket}: {type(e).__name__} - {e}", exc_info=True)
        return None, f"Error de almacenamiento al mover archivo: {str(e)}"

async def delete_files_from_storage(
    supabase_client: SupabaseClient,
    bucket_name: str,
    list_of_file_paths: List[str]
) -> List[Tuple[str, bool, Optional[str]]]:
    if not list_of_file_paths:
        return []
    results = []
    # La función remove puede tomar una lista de paths, así que podemos hacer una sola llamada.
    # Sin embargo, para obtener resultados individuales por archivo, iterar puede ser más claro
    # si la librería no devuelve un desglose claro para operaciones batch.
    # supabase-py v2 .remove() sí devuelve una lista de resultados para cada path.
    try:
        if not list_of_file_paths: # Doble check por si acaso
            return []

        logger.info(f"Intentando borrar los siguientes archivos del bucket '{bucket_name}': {list_of_file_paths}")
        
        # Envolver llamada síncrona
        def _remove_sync():
            return supabase_client.storage.from_(bucket_name).remove(paths=list_of_file_paths)
        
        response_data_list = await asyncio.to_thread(_remove_sync)
        
        # response_data_list debería ser una lista de dicts, uno por cada archivo intentado.
        # Necesitamos mapear estos resultados a nuestros paths originales.
        # Esto es un poco más complejo porque la respuesta no necesariamente mantiene el orden
        # o incluye el path original de forma obvia.
        # Asumamos por ahora que la librería se comporta bien y devuelve en orden o podemos inferirlo.
        # Si la API devuelve un error general para el batch, response_data_list podría ser un dict de error.

        if isinstance(response_data_list, list):
            # Asumiendo que la respuesta tiene el mismo número de elementos que los paths enviados
            # y que están en el mismo orden, o que cada item en response_data_list tiene una
            # forma de identificar a qué archivo corresponde (ej. `item.get('name')`).
            # El SDK de Supabase para Python, para .remove(paths), devuelve una lista de objetos
            # que representan los archivos eliminados (o errores si alguno falló).
            # Cada objeto en la lista devuelta por .remove() suele tener `name`, `id`, `bucket_id`, etc.
            # si fue exitoso, o `error`, `message`, `statusCode` si falló para ese item específico.

            path_to_result_map = {item.get("name"): item for item in response_data_list if item.get("name")}

            for path_attempted in list_of_file_paths:
                # Extraer el nombre del archivo del path para buscarlo en la respuesta
                # Esto asume que path_attempted es como "folder/subfolder/filename.ext"
                # y que item.get("name") en la respuesta es "filename.ext" si el path en `list()` fue solo la carpeta.
                # O si item.get("name") es la ruta completa, entonces podemos comparar directamente.
                # La documentación de Supabase Storage indica que `name` en la respuesta de `remove`
                # es la ruta completa del objeto eliminado.
                
                item_result = path_to_result_map.get(path_attempted)

                if item_result:
                    if item_result.get("error"): # Si el objeto de respuesta tiene un campo de error
                        error_msg = f"Error: {item_result.get('error')}, Mensaje: {item_result.get('message', 'Error desconocido')}"
                        logger.warning(f"Fallo al borrar {bucket_name}/{path_attempted}: {error_msg}")
                        results.append((path_attempted, False, error_msg))
                    else: # Asumimos éxito si no hay error explícito en el item
                        logger.info(f"Archivo {bucket_name}/{path_attempted} borrado exitosamente (según respuesta individual).")
                        results.append((path_attempted, True, None))
                else:
                    # Esto podría pasar si el archivo no existía y `remove` no lo incluye en la respuesta,
                    # o si el mapeo por nombre falló.
                    logger.warning(f"No se encontró resultado específico en la respuesta de borrado para {bucket_name}/{path_attempted}. Asumiendo que no existía o fue borrado.")
                    results.append((path_attempted, True, "No se encontró resultado específico en la respuesta (podría no haber existido)."))
        else:
            # Si la respuesta no es una lista, podría ser un error general del batch.
            error_msg_general = f"Respuesta inesperada o error general del batch al borrar archivos: {response_data_list}"
            logger.error(error_msg_general)
            for path_attempted in list_of_file_paths:
                results.append((path_attempted, False, "Error general del batch de borrado."))
                
    except Exception as e_batch:
        logger.error(f"Excepción general al intentar borrar archivos del bucket '{bucket_name}': {type(e_batch).__name__} - {e_batch}", exc_info=True)
        for path_attempted in list_of_file_paths:
            results.append((path_attempted, False, str(e_batch)))
    return results

# ========================================================================
# NUEVA FUNCIÓN: delete_all_files_in_wip_folder
# ========================================================================
async def delete_all_files_in_folder( # Esta es la versión genérica
    supabase_client: SupabaseClient,
    bucket_name: str,
    folder_path: str # Acepta cualquier path de carpeta
) -> Tuple[bool, Optional[str]]:
    """
    Deletes all files within a specified folder in a Supabase Storage bucket.
    The folder_path should typically end with a '/'.
    """
    # Asegurar que el folder_path termine con '/' para el listado,
    # pero para construir los paths de los archivos a borrar, puede que necesitemos quitarlo.
    if not folder_path.endswith('/'):
        folder_path_for_list = folder_path + '/'
    else:
        folder_path_for_list = folder_path
    
    logger.info(f"Intentando limpiar la carpeta: '{bucket_name}/{folder_path_for_list}'")

    try:
        # --- CORRECCIÓN: Envolver la llamada síncrona .list() en asyncio.to_thread ---
        def _list_sync():
            # Esta función se ejecutará en un hilo separado
            # .list() devuelve una lista de diccionarios directamente o lanza error
            return supabase_client.storage.from_(bucket_name).list(path=folder_path_for_list)

        list_response: List[Dict[str, any]] = await asyncio.to_thread(_list_sync)
        
        if not list_response: # Carpeta vacía o no existe, o error al listar que devuelve None/[]
            logger.info(f"No se encontraron archivos para borrar en {bucket_name}/{folder_path_for_list} o la carpeta no existe/está vacía.")
            return True, None

        # `item['name']` es el nombre del archivo/subcarpeta dentro de `folder_path_for_list`.
        # Necesitamos construir la ruta completa desde la raíz del bucket para .remove().
        files_to_delete_paths: List[str] = []
        for item in list_response:
            if item.get('id') is not None: # Es un archivo (las carpetas tienen id=None en la respuesta de list)
                # Construir el path completo del archivo dentro del bucket
                # folder_path_for_list ya tiene el trailing '/'
                full_file_path = f"{folder_path_for_list}{item['name']}"
                files_to_delete_paths.append(full_file_path)

        if not files_to_delete_paths:
            logger.info(f"La carpeta '{bucket_name}/{folder_path_for_list}' no contiene archivos para eliminar (solo subcarpetas quizás).")
            return True, None

        logger.info(f"Archivos encontrados en '{bucket_name}/{folder_path_for_list}' para eliminar: {files_to_delete_paths}")
        
        # Usar la función delete_files_from_storage que maneja errores individuales
        delete_results = await delete_files_from_storage(supabase_client, bucket_name, files_to_delete_paths)

        all_successful = all(success for _, success, _ in delete_results)
        
        if all_successful:
            logger.info(f"Todos los archivos de la carpeta '{bucket_name}/{folder_path_for_list}' fueron eliminados exitosamente.")
            return True, None
        else:
            errors_encountered = [f"Fallo al borrar {path}: {err_msg}" for path, success, err_msg in delete_results if not success]
            combined_error_message = "; ".join(errors_encountered)
            logger.error(f"Errores al limpiar la carpeta '{bucket_name}/{folder_path_for_list}': {combined_error_message}")
            return False, combined_error_message

    except Exception as e:
        logger.error(f"Excepción al limpiar la carpeta '{bucket_name}/{folder_path_for_list}': {type(e).__name__} - {e}", exc_info=True)
        return False, f"Error general al limpiar carpeta: {str(e)}"

# Y asegúrate de que delete_files_from_storage también maneje correctamente el async con tu SDK:
async def delete_files_from_storage(
    supabase_client: SupabaseClient,
    bucket_name: str,
    list_of_file_paths: List[str]
) -> List[Tuple[str, bool, Optional[str]]]:
    if not list_of_file_paths:
        return []
    results = []
    for file_path in list_of_file_paths:
        try:
            def _remove_sync():
                return supabase_client.storage.from_(bucket_name).remove(paths=[file_path])
            
            response_data_list = await asyncio.to_thread(_remove_sync) # ASUMIENDO que remove es síncrono
            if response_data_list and isinstance(response_data_list, list) and len(response_data_list) > 0:
                item_result = response_data_list[0]
                if item_result.get("error"): # Supabase puede devolver un error por archivo
                    error_msg = f"{item_result.get('error')}: {item_result.get('message', 'Error desconocido')}"
                    logger.warning(f"Fallo al borrar {bucket_name}/{file_path}: {error_msg}")
                    results.append((file_path, False, error_msg))
                else: # Éxito
                    logger.info(f"Archivo {bucket_name}/{file_path} borrado exitosamente.")
                    results.append((file_path, True, None))
            else: # Respuesta inesperada
                logger.warning(f"Respuesta inesperada al borrar {bucket_name}/{file_path}: {response_data_list}")
                results.append((file_path, False, "Respuesta inesperada del servicio de storage al borrar."))
        except Exception as e_single:
            logger.error(f"Excepción borrando archivo {bucket_name}/{file_path}: {type(e_single).__name__} - {e_single}", exc_info=True)
            results.append((file_path, False, str(e_single)))
    return results