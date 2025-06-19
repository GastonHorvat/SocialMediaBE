# app/api/v1/routers/social/connections_router.py
import secrets
import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.oauth_clients import oauth
from app.models.connection_models import ConnectionResponse, AuthorizationURLResponse
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.services.social.connections_service import connections_service
from app.services.oauth_state_service import oauth_state_service

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Códigos de color para la terminal ---
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"

@router.get("", response_model=List[ConnectionResponse], summary="Listar Conexiones Sociales")
def list_connections(current_user: TokenData = Depends(get_current_user)):
    """Obtiene todas las conexiones sociales para la organización del usuario."""
    if not current_user.organization_id:
        return []
    return connections_service.get_connections_by_org(current_user.organization_id)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una Conexión Social")
def delete_connection(connection_id: UUID, current_user: TokenData = Depends(get_current_user)):
    """
    Elimina una conexión social específica, verificando que pertenezca
    a la organización del usuario actual para seguridad.
    """
    connection = connections_service.get_connection_by_id(connection_id)
    if not connection or UUID(connection['organization_id']) != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada o no pertenece a la organización.")
    
    connections_service.delete_connection(connection_id=connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/linkedin/connect", response_model=AuthorizationURLResponse, summary="Iniciar conexión con LinkedIn")
async def connect_linkedin(current_user: TokenData = Depends(get_current_user)):
    """
    Paso 1 del flujo OAuth: Genera una URL de autorización segura y la devuelve al frontend.
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario debe pertenecer a una organización.")

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    await run_in_threadpool(
        oauth_state_service.create_oauth_state,
        state=state,
        code_verifier=code_verifier,
        provider='linkedin',
        user_id=current_user.user_id,
        organization_id=current_user.organization_id
    )

    redirect_uri = settings.LINKEDIN_REDIRECT_URI
    print(f"\n{COLOR_YELLOW}--- PASO 1: CONSTRUYENDO URL DE AUTORIZACIÓN ---")
    print(f"Enviando 'redirect_uri' al navegador: {redirect_uri}")
    print(f"----------------------------------------------------{COLOR_RESET}\n")
    # --- FIN DEL BLOQUE DE DEPURACIÓN 1 ---    
    authorization_url_object = await oauth.linkedin.create_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
        code_verifier=code_verifier
    )
    
    return AuthorizationURLResponse(authorization_url=authorization_url_object['url'])


@router.get("/linkedin/callback", summary="Callback de LinkedIn para finalizar conexión", include_in_schema=False)
async def linkedin_callback(request: Request):
    """
    Paso 2 del flujo OAuth: Procesa la respuesta de LinkedIn, valida el estado,
    intercambia el código por un token y crea la conexión.
    """
    state = request.query_params.get('state')
    frontend_redirect_url = f"{settings.FRONTEND_URL}/settings?tab=connections"

    stored_state_data = await run_in_threadpool(
        oauth_state_service.consume_oauth_state, 
        state=state, 
        provider='linkedin'
    )
    if not stored_state_data:
        error_url = f"{frontend_redirect_url}&status=linkedin_error&message=El estado de la sesión es inválido o ha expirado."
        return RedirectResponse(url=error_url)
    
    payload = stored_state_data['payload']
    user_id = UUID(payload['user_id'])
    organization_id = UUID(payload['organization_id'])

    try:
        code = request.query_params.get('code')
        if not code:
            raise HTTPException(status_code=400, detail="El parámetro 'code' no fue encontrado en la respuesta de LinkedIn.")

        # Se construye la llamada a 'fetch_access_token' con todos los parámetros
        # requeridos explícitamente por la especificación OAuth 2.0 (RFC 6749).
        redirect_uri = settings.LINKEDIN_REDIRECT_URI
        # --- INICIO DEL BLOQUE DE DEPURACIÓN 2 ---
        print(f"\n{COLOR_RED}--- PASO 2: VERIFICACIÓN EN EL CALLBACK ---")
        print(f"Enviando para el intercambio de token con los siguientes parámetros:")
        print(f"  > code:          {code[:30]}...")
        print(f"  > redirect_uri:  {redirect_uri}")
        print(f"-------------------------------------------{COLOR_RESET}\n")
        # --- FIN DEL BLOQUE DE DEPURACIÓN 2 ---
        token_data = await oauth.linkedin.fetch_access_token(
            code=code,
            redirect_uri=redirect_uri, # Requerido por el protocolo para validación.
            code_verifier=stored_state_data['code_verifier'] # Requerido para PKCE.
        )
        
        user_info = await oauth.linkedin.userinfo(token=token_data)
        
        await run_in_threadpool(
            connections_service.create_or_update_connection,
            organization_id=organization_id,
            user_id=user_id,
            platform='linkedin',
            platform_user_id=f"urn:li:person:{user_info['sub']}",
            platform_account_name=user_info.get('name', 'Usuario de LinkedIn'),
            token_data=token_data
        )
        return RedirectResponse(url=f"{frontend_redirect_url}&status=linkedin_success")

    except Exception as e:
        logger.error(f"Error crítico en el callback de LinkedIn: {e}", exc_info=True)
        error_message = getattr(e, 'description', str(e).splitlines()[0] if str(e) else "Ocurrió un error desconocido.")
        error_url = f"{frontend_redirect_url}&status=linkedin_error&message={error_message}"
        return RedirectResponse(url=error_url)