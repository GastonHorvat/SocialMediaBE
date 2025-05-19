# app/api/v1/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from gotrue.errors import AuthApiError # <<< Importación para el error específico de Auth

from app.db.supabase_client import get_supabase_client
from app.models.auth_models import TokenRequestForm, TokenResponse

router = APIRouter()

@router.post(
    "/token",
    # ... (resto del decorador)
)
async def login_for_access_token(
    form_data: TokenRequestForm,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": form_data.email,
            "password": form_data.password
        })


        # Verificar si la respuesta de Supabase contiene la sesión y los tokens
        if auth_response.user and auth_response.session and \
           auth_response.session.access_token and auth_response.session.refresh_token:
            
            print(f"INFO: Inicio de sesión exitoso para el usuario: {auth_response.user.email}")
            return TokenResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                expires_in=auth_response.session.expires_in, # Supabase incluye esto
                # token_type ya tiene "bearer" como default en el modelo Pydantic
                # user_id=str(auth_response.user.id) # Podrías añadirlo si el FE lo necesita inmediatamente
            )
        elif auth_response.error: # auth_response.error es del tipo AuthApiError
            print(f"ERROR: Supabase Auth Error: {auth_response.error.message} (Status: {auth_response.error.status})")
            raise HTTPException(
                status_code=auth_response.error.status,
                detail=auth_response.error.message or "Credenciales incorrectas.",
            )
        else:
            # Caso inesperado donde no hay error claro pero tampoco sesión/tokens
            print(f"ERROR: Respuesta inesperada de Supabase Auth durante login para {form_data.email}: {auth_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Respuesta inesperada del servicio de autenticación.",
            )

    except AuthApiError as e: # Captura explícita si quieres manejarla fuera del flujo de auth_response.error
        print(f"ERROR: Capturado AuthApiError explícitamente: {e.message} (Status: {e.status})")
        raise HTTPException(
            status_code=e.status,
            detail=e.message or "Error de autenticación."
        )
    except Exception as e:
        # Loguear el error `e` de forma más robusta en producción
        print(f"ERROR: Excepción inesperada durante login para {form_data.email}: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error inesperado durante el proceso de inicio de sesión."
        )