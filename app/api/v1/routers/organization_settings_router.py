# app/api/v1/routers/organization_settings_router.py
from fastapi import APIRouter, Depends, HTTPException, status
# from typing import Dict, Any # Ya debería estar de los endpoints anteriores
from uuid import UUID

from app.db.supabase_client import get_supabase_client, Client as SupabaseClient
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.models.organization_models import (
    OrganizationSettingsAIUpdate, 
    OrganizationSettingsAIResponse,
    ContentPreferencesUpdate,     # <--- NUEVO MODELO
    ContentPreferencesResponse    # <--- NUEVO MODELO
)
from postgrest.exceptions import APIError

router = APIRouter()

# --- Endpoint para OBTENER Identidad de Marca IA (el que ya teníamos) ---
@router.get(
    "/ai-identity/", # Cambiando ruta para ser más específico
    response_model=OrganizationSettingsAIResponse,
    summary="Obtener Configuración de Identidad de Marca para IA",
    # ... (descripción, tags sin cambio)
)
async def get_ai_organization_settings(
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")
    try:
        response = supabase.table("organization_settings").select("*").eq("organization_id", str(current_user.organization_id)).maybe_single().execute()
        if response.data:
            settings_data = response.data
            settings_data["ai_brand_personality_tags"] = settings_data.get("ai_brand_personality_tags") or []
            settings_data["ai_keywords_to_use"] = settings_data.get("ai_keywords_to_use") or []
            return OrganizationSettingsAIResponse.model_validate(settings_data)
        else:
            return OrganizationSettingsAIResponse(organization_id=current_user.organization_id)
    except APIError as e: # ... (manejo de error como lo tenías) ...
        print(f"ERROR_ORG_SETTINGS_GET_AI: APIError al obtener configuraciones de IA: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de BD al obtener configuraciones de IA: {e.message}")
    except Exception as e: # ... (manejo de error como lo tenías) ...
        print(f"ERROR_ORG_SETTINGS_GET_AI: Excepción inesperada al obtener configuraciones de IA: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado al obtener configuraciones de IA.")

# --- Endpoint para ACTUALIZAR Identidad de Marca IA (el que ya teníamos) ---
@router.put(
    "/ai-identity/", # Cambiando ruta para ser más específico
    response_model=OrganizationSettingsAIResponse,
    summary="Actualizar Configuración de Identidad de Marca para IA",
    # ... (descripción, tags sin cambio)
)
async def update_ai_organization_settings(
    settings_data: OrganizationSettingsAIUpdate,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id: # ... (verificación como la tenías) ...
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa para modificar configuraciones.")
    update_payload = settings_data.model_dump(exclude_unset=True)
    if "organization_id" in update_payload: del update_payload["organization_id"]
    if not update_payload: # ... (verificación como la tenías) ...
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se proporcionaron datos para actualizar.")
    try:
        response = supabase.table("organization_settings").upsert(
            {**update_payload, "organization_id": str(current_user.organization_id)},
            on_conflict="organization_id"
        ).execute()
        if response.data and isinstance(response.data, list) and len(response.data) > 0:
            updated_data_dict = response.data[0]
            updated_data_dict["ai_brand_personality_tags"] = updated_data_dict.get("ai_brand_personality_tags") or []
            updated_data_dict["ai_keywords_to_use"] = updated_data_dict.get("ai_keywords_to_use") or []
            return OrganizationSettingsAIResponse.model_validate(updated_data_dict)
        else: # ... (manejo de error como lo tenías) ...
            print(f"ERROR_ORG_SETTINGS_PUT_AI: Upsert de config IA no devolvió datos. Respuesta: {response}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar la configuración de IA: no se obtuvieron datos después del upsert.")
    except APIError as e: # ... (manejo de error como lo tenías) ...
        print(f"ERROR_ORG_SETTINGS_PUT_AI: APIError al guardar configuraciones de IA: Code={getattr(e, 'code', 'N/A')}, Msg='{e.message}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de BD al guardar configuraciones de IA: {e.message}")
    except Exception as e: # ... (manejo de error como lo tenías) ...
        print(f"ERROR_ORG_SETTINGS_PUT_AI: Excepción inesperada al guardar configuraciones de IA: {type(e).__name__} - {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al guardar configuraciones de IA: {str(e)}")


# --- NUEVO Endpoint para OBTENER Preferencias de Contenido ---
@router.get(
    "/content-preferences/",
    response_model=ContentPreferencesResponse,
    summary="Obtener Preferencias de Generación de Contenido",
    description="Recupera las preferencias de generación automática de hashtags y emojis para la organización del usuario.",
    tags=["Organization Settings"]
)
async def get_content_preferences(
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")
    
    try:
        response = (
            supabase.table("organization_settings")
            .select("organization_id, prefs_auto_hashtags_enabled, prefs_auto_hashtags_count, prefs_auto_hashtags_strategy, prefs_auto_emojis_enabled, prefs_auto_emojis_style, updated_at")
            .eq("organization_id", str(current_user.organization_id))
            .maybe_single()
            .execute()
        )

        if response.data:
            # Los defaults del modelo Pydantic se encargarán si algún campo es None
            return ContentPreferencesResponse.model_validate(response.data)
        else:
            # Devolver respuesta con valores por defecto del modelo Pydantic
            return ContentPreferencesResponse(organization_id=current_user.organization_id)
            # Alternativa: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron preferencias de contenido para esta organización.")

    except APIError as e:
        print(f"ERROR_ORG_SETTINGS_GET_PREFS: APIError al obtener preferencias: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de BD al obtener preferencias: {e.message}")
    except Exception as e:
        print(f"ERROR_ORG_SETTINGS_GET_PREFS: Excepción inesperada al obtener preferencias: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado al obtener preferencias.")


# --- NUEVO Endpoint para ACTUALIZAR Preferencias de Contenido ---
@router.put(
    "/content-preferences/",
    response_model=ContentPreferencesResponse,
    summary="Actualizar Preferencias de Generación de Contenido",
    description="Crea o actualiza las preferencias de generación automática de hashtags y emojis.",
    tags=["Organization Settings"]
)
async def update_content_preferences(
    preferences_data: ContentPreferencesUpdate,
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no asociado a una organización activa.")

    update_payload = preferences_data.model_dump(exclude_unset=True)
    if "organization_id" in update_payload: del update_payload["organization_id"]
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se proporcionaron datos para actualizar.")

    try:
        response = (
            supabase.table("organization_settings")
            .upsert(
                {**update_payload, "organization_id": str(current_user.organization_id)},
                on_conflict="organization_id"
            )
            .execute() # Upsert y ejecutar
        )

        if response.data and isinstance(response.data, list) and len(response.data) > 0:
            # Necesitamos hacer un SELECT después del upsert para obtener todos los campos
            # necesarios para ContentPreferencesResponse, ya que upsert solo devuelve los campos que actualizó
            # o todos si es una inserción (dependiendo de la config de PostgREST).
            # Para ser seguros, hacemos un select explícito.
            refreshed_settings_response = (
                supabase.table("organization_settings")
                .select("organization_id, prefs_auto_hashtags_enabled, prefs_auto_hashtags_count, prefs_auto_hashtags_strategy, prefs_auto_emojis_enabled, prefs_auto_emojis_style, updated_at")
                .eq("organization_id", str(current_user.organization_id))
                .single() # Sabemos que existe después del upsert
                .execute()
            )
            if refreshed_settings_response.data:
                return ContentPreferencesResponse.model_validate(refreshed_settings_response.data)
            else:
                # Esto sería muy inesperado
                print(f"ERROR_ORG_SETTINGS_PUT_PREFS: No se pudo recuperar la configuración después del upsert.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al confirmar guardado de preferencias.")

        else:
            print(f"ERROR_ORG_SETTINGS_PUT_PREFS: Upsert de preferencias no devolvió datos. Respuesta: {response}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar preferencias: no se obtuvieron datos después del upsert.")
            
    except APIError as e:
        print(f"ERROR_ORG_SETTINGS_PUT_PREFS: APIError al guardar preferencias: Code={getattr(e, 'code', 'N/A')}, Msg='{e.message}'")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de BD al guardar preferencias: {e.message}")
    except Exception as e:
        print(f"ERROR_ORG_SETTINGS_PUT_PREFS: Excepción inesperada al guardar preferencias: {type(e).__name__} - {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al guardar preferencias: {str(e)}")