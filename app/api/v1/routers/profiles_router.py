# app/api/v1/routers/profiles_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any # Asegúrate de que Optional, Dict y Any estén aquí
from uuid import UUID

from app.db.supabase_client import get_supabase_client, SupabaseClient
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.models.profile_models import ProfileUpdate, ProfileResponse # Ajusta la ruta si es necesario
from postgrest.exceptions import APIError
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/me",
    response_model=ProfileResponse, # Usar el modelo actualizado
    summary="Obtener Perfil del Usuario Actual con Detalles de Organización",
    description="Recupera el perfil del usuario autenticado, incluyendo su email, ID de organización y rol en la organización.",
    tags=["Profiles"]
)
async def get_current_user_profile(
    current_user: TokenData = Depends(get_current_user), # TokenData ya tiene user_id, org_id, role
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    user_id = current_user.user_id
    
    profile_data_from_db: Optional[dict] = None
    user_email_from_auth: Optional[str] = None # Renombrado para claridad

    logger.info(f"PROFILE_ME - Solicitando perfil para user_id: {user_id}, org_id: {current_user.organization_id}, role: {current_user.role}")

    # --- Bloque 1: Obtener datos de la tabla 'profiles' ---
    try:
        # SIN await (asumiendo comportamiento síncrono de .execute() en tu entorno)
        profile_response = (
            supabase.table("profiles")
            .select("full_name, avatar_url, timezone, created_at, updated_at") # Seleccionar solo los campos de 'profiles'
            .eq("id", str(user_id))
            .single() # .single() es síncrono
            .execute()
        )
        
        if profile_response.data:
            profile_data_from_db = profile_response.data
            logger.debug(f"PROFILE_ME - Datos de 'profiles' obtenidos para {user_id}: {profile_data_from_db}")
        # else: # No se encontró perfil en 'profiles', profile_data_from_db permanecerá None

    except APIError as e:
        if str(getattr(e, 'code', '')) == 'PGRST116': 
             logger.warning(f"PROFILE_ME - No se encontró perfil único en 'profiles' para {user_id} (PGRST116).")
             profile_data_from_db = None 
        else:
            logger.error(f"PROFILE_ME - APIError al obtener datos de 'profiles' para {user_id}: Code={getattr(e, 'code', 'N/A')}, Msg='{e.message}'", exc_info=True)
            profile_data_from_db = None 
    except Exception as e_profiles:
        logger.error(f"PROFILE_ME - Excepción inesperada al obtener datos de 'profiles' para {user_id}: {type(e_profiles).__name__} - {e_profiles}", exc_info=True)
        profile_data_from_db = None

    # --- Bloque 2: Obtener el email de auth.users (si no está ya en TokenData) ---
    # Si tu TokenData ya incluye el email (extraído del JWT en get_current_user), puedes omitir este bloque.
    # Asumiré que necesitas obtenerlo aquí.
    # NOTA: supabase.auth.admin.get_user_by_id() requiere privilegios de admin (service_role_key).
    # Si tu `supabase_client` está instanciado con la service_role_key, esto funcionará.
    # Si no, y si el email está en el JWT, es mejor extraerlo en `get_current_user` y añadirlo a `TokenData`.
    
    # Alternativa más simple si el email está en el JWT y lo añades a TokenData:
    # user_email_from_auth = current_user.email (si TokenData.email existe)

    try:
        logger.debug(f"PROFILE_ME - Intentando obtener email para user_id: {user_id} vía admin API.")
        # Esta es una llamada de admin, asegúrate que tu cliente `supabase` tenga los permisos.
        # Para obtener el email del usuario actual autenticado, es más común usar `supabase.auth.get_user()`
        # pasando el token JWT actual, pero `get_current_user` ya validó el token.
        # Si `TokenData` ya tuviera el email, sería más directo.
        # Por ahora, mantendré tu lógica con get_user_by_id, asumiendo que `supabase` es un cliente admin.

        auth_user_api_response = supabase.auth.admin.get_user_by_id(user_id=str(user_id))
                
        if auth_user_api_response and hasattr(auth_user_api_response, 'user') and auth_user_api_response.user and hasattr(auth_user_api_response.user, 'email'):
            user_email_from_auth = auth_user_api_response.user.email
            logger.debug(f"PROFILE_ME - Email obtenido de auth.admin API: {user_email_from_auth}")
        else:
            logger.warning(f"PROFILE_ME - No se pudo obtener el email para {user_id} desde auth.admin API. Respuesta: {auth_user_api_response}")
            
    except APIError as e_auth_api:
        logger.error(f"PROFILE_ME - APIError al obtener user de auth.admin API para {user_id}: {e_auth_api.message if hasattr(e_auth_api, 'message') else e_auth_api}", exc_info=True)
    except Exception as e_auth:
        logger.error(f"PROFILE_ME - Excepción genérica al obtener user de auth.admin API para {user_id}: {type(e_auth).__name__} - {e_auth}", exc_info=True)


    # --- Bloque 3: Construir la respuesta final ---
    # Usar los datos de TokenData directamente para id, organization_id, y role
    response_payload = {
        "id": current_user.user_id,
        "email": user_email_from_auth, # Email obtenido de auth.users
        "organization_id": current_user.organization_id, # <--- DE TokenData
        "role": current_user.role                        # <--- DE TokenData
    }

    # Añadir datos de la tabla 'profiles' si se obtuvieron
    if profile_data_from_db:
        # Asegurarse de no sobrescribir id o email si vinieran de profile_data_from_db
        # con valores diferentes a los de auth.
        # Los campos de profile_data_from_db son: full_name, avatar_url, timezone, created_at, updated_at
        response_payload.update({
            k: v for k, v in profile_data_from_db.items() 
            if k in ["full_name", "avatar_url", "timezone", "created_at", "updated_at"]
        })
    
    logger.debug(f"PROFILE_ME - Payload final para validación de ProfileResponse: {response_payload}")
    
    try:
        validated_response = ProfileResponse.model_validate(response_payload)
        logger.info(f"PROFILE_ME - Perfil devuelto exitosamente para user {user_id}.")
        return validated_response
    except Exception as val_err: 
        logger.error(f"PROFILE_ME - Error al validar ProfileResponse para user {user_id}: {val_err}. Payload intentado: {response_payload}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar datos del perfil del usuario.")


@router.put(
    "/me",
    response_model=ProfileResponse,
    summary="Actualizar Perfil del Usuario Actual",
    description="Actualiza los campos del perfil del usuario autenticado (nombre, avatar, zona horaria).",
    tags=["Profiles"]
)
async def update_current_user_profile(
    profile_data: ProfileUpdate,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    user_id = current_user.user_id
    update_payload = profile_data.model_dump(exclude_unset=True)

    if not update_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron datos para actualizar."
        )
    
    try:
        update_response = (
            supabase.table("profiles")
            .update(update_payload)
            .eq("id", str(user_id))
            .execute()
        )

        # Verificar si la actualización afectó a alguna fila.
        # .execute() en un update devuelve .data como una lista de los registros actualizados.
        # Si la lista está vacía, no se actualizó nada (ej. el 'id' no existía).
        if not update_response.data or len(update_response.data) == 0:
            print(f"WARN_PROFILE_PUT: No se actualizó ninguna fila para el perfil del usuario {user_id}. ¿Existe el perfil en la tabla 'profiles'?")
            # Podrías considerar un upsert si el perfil podría no existir, o tratar esto como un error.
            # Por ahora, si no actualizó, es posible que el perfil no exista, aunque el trigger debería haberlo creado.
            # Devolveremos un 404 en este caso.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado para actualizar. Contacta a soporte si el problema persiste.")
        
        # Si la actualización fue exitosa, obtener el perfil completo para devolverlo
        # (esto incluye el email de auth.users y cualquier campo no actualizado de profiles)
        # Reutilizamos la lógica de get_current_user_profile.
        # Asegúrate de que no haya await aquí si get_current_user_profile es una función normal
        # y solo la llamada dentro de ella a supabase.execute() es síncrona.
        # Como get_current_user_profile es async, necesitamos await.
        
        # print(f"DEBUG_PROFILE_PUT: Perfil actualizado, obteniendo datos completos para la respuesta.")
        return await get_current_user_profile(current_user=current_user, supabase=supabase)
            
    except APIError as e:
        print(f"ERROR_PROFILE_PUT: APIError al actualizar perfil: Code={getattr(e, 'code', 'N/A')}, Msg='{getattr(e, 'message', str(e))}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de base de datos al actualizar perfil: {getattr(e, 'message', str(e))}")
    except Exception as e:
        print(f"ERROR_PROFILE_PUT: Excepción inesperada al actualizar perfil: {type(e).__name__} - {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al actualizar perfil: {str(e)}")