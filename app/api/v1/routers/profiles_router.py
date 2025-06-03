# app/api/v1/routers/profiles_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any # Asegúrate de que Optional, Dict y Any estén aquí
from uuid import UUID

from app.db.supabase_client import get_supabase_client, SupabaseClient
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.models.profile_models import ProfileUpdate, ProfileResponse # Ajusta la ruta si es necesario
from postgrest.exceptions import APIError

router = APIRouter()

@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Obtener Perfil del Usuario Actual",
    description="Recupera el perfil del usuario autenticado, incluyendo su email de auth.users.",
    tags=["Profiles"]
)
async def get_current_user_profile(
    current_user: TokenData = Depends(get_current_user), # (1)
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    user_id = current_user.user_id # (2)
    
    profile_data_from_db: Optional[dict] = None
    user_email: Optional[str] = None

    # print(f"INFO_PROFILE_GET: Solicitando perfil para user_id: {user_id}")

    # --- Bloque 1: Obtener datos de la tabla 'profiles' ---
    try:
        profile_response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", str(user_id)) # (3)
            .single() # (4)
            .execute()
        )
        
        if profile_response.data: # (5)
            profile_data_from_db = profile_response.data
        # else: # No es estrictamente necesario un else aquí si PGRST116 se maneja abajo

    except APIError as e: # (6)
        # PGRST116: "The result contains 0 rows" (o a veces "more than 1") cuando .single() no encuentra exactamente uno.
        if str(getattr(e, 'code', '')) == 'PGRST116': 
             print(f"WARN_PROFILE_GET: No se encontró perfil único en la tabla 'profiles' para el usuario {user_id} (PGRST116). Se usarán defaults/email solo.")
             profile_data_from_db = None 
        else: # Otro tipo de APIError de la base de datos
            print(f"ERROR_PROFILE_GET: APIError al obtener datos de 'profiles': Code={getattr(e, 'code', 'N/A')}, Msg='{getattr(e, 'message', str(e))}'")
            # Considera si quieres fallar aquí o intentar obtener el email. Por ahora, continuamos.
            profile_data_from_db = None 
    except Exception as e_profiles: # Otras excepciones (ej. de red, timeouts si no son APIError)
        print(f"ERROR_PROFILE_GET: Excepción inesperada al obtener datos de 'profiles': {type(e_profiles).__name__} - {e_profiles}")
        profile_data_from_db = None # Asegurar que es None para continuar y devolver lo que se tenga

    # --- Bloque 2: Obtener el email de la tabla 'auth.users' ---
    try:
        # print(f"DEBUG_PROFILE_GET: Intentando obtener email para user_id: {user_id}")
        auth_user_response = supabase.auth.admin.get_user_by_id(str(user_id)) # (7)
        
        if auth_user_response and hasattr(auth_user_response, 'user') and auth_user_response.user:
            user_email = auth_user_response.user.email
            # print(f"DEBUG_PROFILE_GET: Email obtenido: {user_email}")
        else:
            print(f"WARN_PROFILE_GET: No se pudo obtener el objeto usuario (y por ende el email) para {user_id} desde auth.users vía admin API. Respuesta: {auth_user_response}")
            # user_email permanecerá None
            
    except APIError as e_auth_api: # Capturar APIError de Supabase Auth
        print(f"ERROR_PROFILE_GET: APIError al obtener datos de auth.users con admin API: {type(e_auth_api).__name__} - {e_auth_api.message if hasattr(e_auth_api, 'message') else e_auth_api}")
        user_email = None
    except Exception as e_auth: # Otras excepciones
        print(f"ERROR_PROFILE_GET: Excepción genérica al obtener datos de auth.users con admin API: {type(e_auth).__name__} - {e_auth}")
        user_email = None

    # --- Bloque 3: Construir la respuesta final ---
    # Crear un diccionario base para construir ProfileResponse
    response_payload = {"id": user_id, "email": user_email} # (8)

    if profile_data_from_db: # (9)
        response_payload.update(profile_data_from_db)
    
    try:
        # Pydantic usará los defaults de ProfileResponse para campos no presentes en response_payload
        # (ej. timezone="UTC" si no vino de la DB)
        return ProfileResponse.model_validate(response_payload) # (10)
    except Exception as val_err: 
        print(f"ERROR_PROFILE_GET: Error al validar ProfileResponse: {val_err}. Payload intentado: {response_payload}")
        raise HTTPException(status_code=500, detail="Error al procesar datos del perfil.")


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