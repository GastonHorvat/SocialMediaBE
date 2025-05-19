# app/db/supabase_client.py
from supabase import create_client, Client
from app.core.config import settings

# Inicializar el cliente de Supabase una vez
# Si settings.SUPABASE_URL o settings.SUPABASE_KEY están vacíos, create_client fallará.
# Asegúrate de que tu .env está configurado correctamente.
if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file or environment variables")

supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_supabase_client() -> Client:
    """
    Dependencia para obtener el cliente de Supabase.
    En el futuro, podría manejar un pool de conexiones o configuraciones más avanzadas.
    """
    return supabase_client

# Ejemplo de cómo podrías usarlo con el token del usuario si el frontend lo envía
# y tu backend lo valida y luego lo pasa a Supabase para que RLS funcione:
# def get_supabase_user_client(user_jwt: str) -> Client:
#     return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options={"headers": {"Authorization": f"Bearer {user_jwt}"}})