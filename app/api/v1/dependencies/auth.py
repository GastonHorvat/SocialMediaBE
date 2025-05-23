# app/api/v1/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.db.supabase_client import get_supabase_client, Client
# Asumiendo supabase-py >= 2.0, que usa postgrest-py
from postgrest.exceptions import APIError
# Si la anterior falla, prueba: from supabase.lib.errors import APIError (para versiones más antiguas)


oauth2_scheme = HTTPBearer()

class TokenData(BaseModel):
    user_id: UUID
    organization_id: Optional[UUID] = None
    role: Optional[str] = None

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    supabase: Client = Depends(get_supabase_client) # Inyecta el cliente Supabase
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None or token.scheme.lower() != "bearer":
        raise credentials_exception
    
    jwt_token = token.credentials

    try:
        secret_to_use = settings.SUPABASE_JWT_SECRET
        payload = jwt.decode(
            jwt_token, 
            secret_to_use,
            algorithms=["HS256"], 
            audience="authenticated" # Verifica que esta sea la audiencia correcta para tus tokens
        )
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            print("AUTH_ERROR: 'sub' (user_id) no encontrado en el payload del token.")
            raise credentials_exception
        
        user_uuid = UUID(user_id_str)

        # --- Inicio: Obtener organization_id y role ---
        user_organization_id: Optional[UUID] = None
        user_role: Optional[str] = None

        try:
            # print(f"AUTH_DEBUG: Consultando organization_members para user_uuid='{user_uuid}'")
            membership_response = (
                supabase.table("organization_members")
                .select("organization_id, role")
                .eq("user_id", str(user_uuid))
                .order("joined_at", desc=False) # Tomar la membresía más antigua
                .limit(1)
                .maybe_single() # Espera un objeto o None (sin lanzar error si no se encuentra)
                .execute()
            )
            
            # Descomenta para depuración profunda si es necesario:
            # print(f"AUTH_DEBUG: Raw membership_response object: {membership_response}")
            # print(f"AUTH_DEBUG: Raw membership_response.data: {getattr(membership_response, 'data', 'No data attr')}")
            # print(f"AUTH_DEBUG: Raw membership_response.error: {getattr(membership_response, 'error', 'No error attr')}")
            # print(f"AUTH_DEBUG: Raw membership_response.status_code: {getattr(membership_response, 'status_code', 'No status_code attr')}")

            # Con .maybe_single(), esperamos que .data sea el diccionario del objeto o None
            if hasattr(membership_response, 'data') and membership_response.data is not None:
                user_organization_id = UUID(membership_response.data["organization_id"])
                user_role = membership_response.data["role"]
                print(f"AUTH_INFO: Membresía encontrada (vía .data) para {user_uuid}: org_id={user_organization_id}, role={user_role}")
            else:
                # Esto se alcanza si .data es None.
                # El log de error anterior (APIError 204) sugiere que .execute() está lanzando una excepción
                # ANTES de que podamos verificar .data. Por eso el bloque except APIError es crucial.
                status_code_info = f"status_code={getattr(membership_response, 'status_code', 'N/A')}"
                print(f"AUTH_INFO: No se encontró membresía (membership_response.data es None) en organization_members para {user_uuid}. {status_code_info}.")

        except APIError as api_exc:
            # Esto captura el error que estás viendo si supabase-py lanza APIError por un 204.
            error_code = getattr(api_exc, 'code', '')
            error_message = getattr(api_exc, 'message', str(api_exc))
            # print(f"AUTH_DEBUG: APIError capturada: code='{error_code}', message='{error_message}'")

            if str(error_code) == '204': # PostgREST devuelve 204 para .maybe_single() si no hay datos
                print(f"AUTH_INFO: No se encontró membresía en organization_members para {user_uuid} (manejado APIError code 204). organization_id y role serán None.")
                # user_organization_id y user_role ya son None por defecto, así que no hacemos nada aquí.
            else:
                # Es otro tipo de APIError (ej. 400, 401, 403, 500 de PostgREST), esto es un error real.
                print(f"AUTH_ERROR: APIError (no 204) al consultar organization_members para {user_uuid}: code='{error_code}', message='{error_message}'")
                # Considera si deberías lanzar una HTTPException aquí para errores PostgREST no-204.
                # Por ejemplo: raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error de base de datos: {error_message}")
        except Exception as db_exc:
            # Otros errores inesperados (no APIError) durante la consulta de membresía.
            print(f"AUTH_ERROR: Excepción genérica al consultar organization_members para {user_uuid}: {type(db_exc).__name__} - {db_exc}")

        # --- Fin: Obtener organization_id y role ---
        
        # print(f"AUTH_DEBUG: Devolviendo TokenData: user_id={user_uuid}, organization_id={user_organization_id}, role={user_role}")
        return TokenData(
            user_id=user_uuid, 
            organization_id=user_organization_id,
            role=user_role
        )

    except JWTError as e:
        print(f"AUTH_ERROR: JWTError al decodificar token: {e}")
        raise credentials_exception
    except ValueError as ve: # Error al convertir string a UUID
        print(f"AUTH_ERROR: ValueError (probablemente conversión de UUID inválido): {ve}")
        raise credentials_exception
    except Exception as e: # Otra excepción inesperada en el flujo principal de get_current_user
        print(f"AUTH_ERROR: Excepción inesperada en get_current_user (fuera de la consulta de membresía): {type(e).__name__} - {e}")
        raise credentials_exception