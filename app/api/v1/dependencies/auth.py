# app/api/v1/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError 
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List # Asegúrate de que List esté importado

from app.core.config import settings
from app.db.supabase_client import get_supabase_client, SupabaseClient 
from postgrest.exceptions import APIError

oauth2_scheme = HTTPBearer()

class TokenData(BaseModel):
    user_id: UUID
    organization_id: Optional[UUID] = None
    role: Optional[str] = None

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> TokenData:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (token issue or user not found)",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None or token.scheme.lower() != "bearer":
        # print("AUTH_ERROR: Token es None o el scheme no es 'bearer'.") # Puedes descomentar para debug si es necesario
        raise credentials_exception
    
    jwt_token = token.credentials
    user_uuid: Optional[UUID] = None

    try:
        secret_to_use = settings.SUPABASE_JWT_SECRET
        payload = jwt.decode(
            jwt_token, 
            secret_to_use,
            algorithms=["HS256"], 
            audience="authenticated"
        )
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            print("AUTH_ERROR: 'sub' (user_id) no encontrado en el payload del token.")
            raise credentials_exception
        user_uuid = UUID(user_id_str)
    except jwt.ExpiredSignatureError as exp_e:
        print(f"AUTH_ERROR: ¡EL TOKEN HA CADUCADO! Error: {type(exp_e).__name__} - {exp_e}")
        raise credentials_exception
    except JWTError as e:
        print(f"AUTH_ERROR: JWTError (no expiración) durante decodificación: {type(e).__name__} - {e}")
        raise credentials_exception
    except ValueError as ve:
        print(f"AUTH_ERROR: ValueError (conversión de user_id a UUID inválido): {ve}")
        raise credentials_exception
    except Exception as e:
        print(f"AUTH_ERROR: Excepción inesperada durante decodificación de token: {type(e).__name__} - {e}")
        raise credentials_exception

    if user_uuid is None:
        print("AUTH_CRITICAL_ERROR: user_uuid es None después de decodificación.")
        raise credentials_exception

    user_organization_id: Optional[UUID] = None
    user_role: Optional[str] = None

    # print(f"AUTH_LOGIC: Iniciando consulta de membresía para user_uuid='{str(user_uuid)}' (sin .maybe_single)") # Log de inicio de esta sección
    try:
        membership_response = (
            supabase.table("organization_members")
            .select("organization_id, role")
            .eq("user_id", str(user_uuid))
            .order("joined_at", desc=False) 
            .limit(1) # Asegura que solo procesamos una si múltiples existen
            .execute() # Usar execute() directamente
        )
        
        # status_code = getattr(membership_response, 'status_code', "N/A")
        # print(f"AUTH_LOGIC: Respuesta de consulta de membresía - Status: {status_code}, Data: {getattr(membership_response, 'data', 'N/A')}")

        # .execute() para un select devuelve .data como una lista.
        # Si no hay coincidencias, .data será una lista vacía []. El status code debería ser 200 OK.
        if hasattr(membership_response, 'data') and isinstance(membership_response.data, list) and len(membership_response.data) > 0:
            first_membership = membership_response.data[0]
            user_organization_id = UUID(first_membership["organization_id"])
            user_role = first_membership["role"]
            print(f"AUTH_LOGIC_INFO: Membresía encontrada para {user_uuid}: org_id={user_organization_id}, role={user_role}")
        else:
            status_code = getattr(membership_response, 'status_code', "N/A") # Para loguear si es inesperado
            print(f"AUTH_LOGIC_INFO: No se encontró membresía en organization_members para {user_uuid} (data vacía/None tras .execute()). Status: {status_code}")
            # user_organization_id y user_role permanecerán None, que es correcto.

    except APIError as api_exc: # Para errores de PostgREST (ej. tabla no existe, error de sintaxis, permisos si no fuera service_role)
        error_code = getattr(api_exc, 'code', '')
        error_message = getattr(api_exc, 'message', str(api_exc))
        print(f"AUTH_LOGIC_ERROR: APIError al consultar organization_members: code='{error_code}', message='{error_message}'")
    except ValueError as ve_org_uuid: # Error al convertir organization_id de la DB a UUID
        print(f"AUTH_LOGIC_ERROR: ValueError al convertir organization_id de la BD a UUID: {ve_org_uuid}")
    except Exception as db_exc:
        print(f"AUTH_LOGIC_ERROR: Excepción genérica al consultar organization_members: {type(db_exc).__name__} - {db_exc}")
    
    # print(f"AUTH_LOGIC: Finalizando get_current_user. org_id='{user_organization_id}', role='{user_role}'")
    return TokenData(
        user_id=user_uuid, 
        organization_id=user_organization_id,
        role=user_role
    )