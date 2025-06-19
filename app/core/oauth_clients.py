# app/core/oauth_clients.py
from authlib.integrations.starlette_client import OAuth
from app.core.config import settings

# Creamos una instancia global de OAuth que será utilizada por los routers.
# Esta instancia manejará las sesiones y los flujos de redirección.
oauth = OAuth()

# --- REGISTRO DEL PROVEEDOR OAUTH: LINKEDIN ---
# Aquí definimos todos los parámetros necesarios para que Authlib pueda
# orquestar el flujo de "Authorization Code Grant with PKCE" con LinkedIn.

# Documentación Oficial de Referencia:
# Flujo de Autorización: https://learn.microsoft.com/es-es/linkedin/shared/authentication/authorization-code-flow
# Endpoint UserInfo (OIDC): https://learn.microsoft.com/es-es/linkedin/shared/integrations/people/userinfo-endpoint

oauth.register(
    name='linkedin',
    client_id=settings.LINKEDIN_CLIENT_ID,
    client_secret=settings.LINKEDIN_CLIENT_SECRET,
    
    # URL a la que se redirige al usuario para que inicie sesión y conceda permisos.
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    
    # URL a la que nuestro backend llamará para intercambiar el 'code' por un 'access_token'.
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    
    # URL base para futuras llamadas a la API de LinkedIn (ej. para obtener perfil).
    api_base_url='https://api.linkedin.com/v2/',

    # Se añade la redirect_uri a la configuración central del cliente. Authlib ahora la conocerá y la usará por defecto para este proveedor.
    redirect_uri=settings.LINKEDIN_REDIRECT_URI,
    
    # El endpoint estándar de OpenID Connect que devuelve la información del usuario.
    # Authlib lo usará automáticamente para obtener los datos del perfil tras el login.
    userinfo_endpoint='userinfo', # Relativo a api_base_url
    
    client_kwargs={
        # Los scopes que solicitamos, separados por espacios.
        # 'openid profile email' son para el flujo de identidad de OpenID Connect.
        # 'w_member_social' es el permiso para poder publicar en nombre del usuario.
        'scope': 'openid profile email w_member_social',
        
        # Indica cómo se envían las credenciales del cliente al solicitar el token.
        # 'client_secret_post' es el método requerido por LinkedIn.
        'token_endpoint_auth_method': 'client_secret_post',
    },
)