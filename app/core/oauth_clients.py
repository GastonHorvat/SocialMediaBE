# app/core/oauth_clients.py
# VERSIÓN FINAL - SIGUIENDO LA DOCUMENTACIÓN DE AUTHLIB PARA FASTAPI

from authlib.integrations.starlette_client import OAuth
from app.core.config import settings

oauth = OAuth()

oauth.register(
    name='linkedin',
    client_id=settings.LINKEDIN_CLIENT_ID,
    client_secret=settings.LINKEDIN_CLIENT_SECRET,
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    api_base_url='https://api.linkedin.com/v2/',
    userinfo_endpoint='https://api.linkedin.com/v2/userinfo',
    client_auth_method='client_secret_post',
    client_kwargs={'scope': 'openid profile email w_member_social'}
)