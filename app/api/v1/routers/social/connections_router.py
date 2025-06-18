# app/api/v1/routers/social/connections_router.py
# VERSIÓN CORREGIDA - SOLUCIONANDO PROBLEMAS DE OAUTH
import httpx
import json
import secrets
import logging

from typing import List
from uuid import UUID
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from authlib.common.urls import add_params_to_uri
from urllib.parse import urlencode

from app.core.config import settings
from app.core.oauth_clients import oauth
from app.models.connection_models import ConnectionResponse, AuthorizationURLResponse
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.services.social.connections_service import connections_service
from app.services.oauth_state_service import oauth_state_service
from app.api.v1.dependencies.resources import get_valid_connection_for_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/linkedin/connect",
    response_model=AuthorizationURLResponse,
    summary="1. Iniciar Conexión con LinkedIn (DB State)"
)
async def linkedin_connect_db_state(current_user: TokenData = Depends(get_current_user)):
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario debe pertenecer a una organización.")
    
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = create_s256_code_challenge(code_verifier)

    # Guardamos los secretos en la base de datos
    oauth_state_service.create_oauth_state(
        state=state, code_verifier=code_verifier, provider="linkedin",
        user_id=current_user.user_id, organization_id=current_user.organization_id
    )

    params = {
        'response_type': 'code', 
        'client_id': settings.LINKEDIN_CLIENT_ID,
        'redirect_uri': settings.LINKEDIN_REDIRECT_URI, 
        'state': state,
        'scope': 'openid profile email w_member_social',
        'code_challenge': code_challenge, 
        'code_challenge_method': 'S256',
    }
    authorization_url = add_params_to_uri('https://www.linkedin.com/oauth/v2/authorization', params)

    return {"authorization_url": authorization_url}

@router.get(
    "/linkedin/callback",
    summary="2. Manejar Callback de LinkedIn (DB State)"
)
async def linkedin_callback_db_state(request: Request):
    frontend_connections_url = f"{settings.FRONTEND_URL}/settings?tab=connections"
    
    state_from_url = request.query_params.get('state')
    # ... (el resto de la lógica de consumir el estado de la DB no cambia)
    stored_data = oauth_state_service.consume_oauth_state(state=state_from_url, provider="linkedin")
    # ...
    code_verifier = stored_data["code_verifier"]
    user_id = UUID(stored_data["payload"]["user_id"])
    organization_id = UUID(stored_data["payload"]["organization_id"])
    code_from_url = request.query_params.get('code')

    if not code_from_url:
        return RedirectResponse(f"{frontend_connections_url}&status=linkedin_error&message=CodeMissing")

    try:
        # --- INICIO DE LA IMPLEMENTACIÓN MANUAL DEFINITIVA ---
        
        token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        
        # 1. Creamos el payload como un diccionario Python.
        payload = {
            'grant_type': 'authorization_code',
            'code': code_from_url,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
            'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
        }
        # Añadimos PKCE si es necesario
        if code_verifier:
            payload['code_verifier'] = code_verifier

        # 2. LA MAGIA: Codificamos manualmente el payload a un string 'application/x-www-form-urlencoded'.
        #    Esto nos da control total sobre el formato del cuerpo.
        encoded_payload = urlencode(payload)
        
        # 3. La cabecera, simple y estricta.
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        # 4. Hacemos la llamada con httpx, pero pasamos el cuerpo como 'content',
        #    no como 'data', para que httpx no intente re-codificar nada.
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers, content=encoded_payload)
            response.raise_for_status()
            token_data = response.json()
            
        # --- FIN DE LA IMPLEMENTACIÓN MANUAL ---
        
        # El resto del flujo no cambia, porque ya sabemos que funciona.
        resp = await oauth.linkedin.get('userinfo', token=token_data)
        resp.raise_for_status()
        user_info = resp.json()

        await connections_service.create_or_update_linkedin_connection(
            organization_id=organization_id, connected_by_user_id=user_id,
            linkedin_user_id=user_info.get('sub'), profile_data=user_info, token_data=token_data
        )
        
        return RedirectResponse(f"{frontend_connections_url}&status=linkedin_success")

    except httpx.HTTPStatusError as e:
        logger.error(f"[CALLBACK] Error HTTP de LinkedIn: {e.response.status_code} - {e.response.text}", exc_info=True)
        return RedirectResponse(f"{frontend_connections_url}&status=linkedin_error&message=TokenFetchError")
    
    except Exception as e:
        logger.error(f"[CALLBACK] Error procesando el callback: {e}", exc_info=True)
        return RedirectResponse(f"{frontend_connections_url}&status=linkedin_error&message={type(e).__name__}")

@router.get("", response_model=List[ConnectionResponse], summary="Listar Conexiones Sociales")
async def list_connections(current_user: TokenData = Depends(get_current_user)):
    if not current_user.organization_id: 
        return []
    return await connections_service.get_connections_by_org(current_user.organization_id)

@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una Conexión Social")
async def delete_connection(connection: dict = Depends(get_valid_connection_for_user)):
    connections_service.delete_connection(connection_id=UUID(connection['id']))
    return Response(status_code=status.HTTP_204_NO_CONTENT)