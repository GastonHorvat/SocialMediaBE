# app/core/config.py
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv() 

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str # Pydantic cargará el valor correcto de 88 caracteres desde .env

    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
try:
    settings = Settings()
    print("--- SETTINGS LOADED ---")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL[:20] if settings.SUPABASE_URL else 'NO CARGADA'}")
    print(f"SUPABASE_KEY: {settings.SUPABASE_KEY[:10] if settings.SUPABASE_KEY else 'NO CARGADA'}...")
    print(f"SUPABASE_JWT_SECRET (len): {len(settings.SUPABASE_JWT_SECRET) if settings.SUPABASE_JWT_SECRET else 'NO CARGADA'}") # Debería ser 88
    print(f"-----------------------")
except Exception as e:
    print(f"!!! ERROR AL CARGAR SETTINGS: {e}")
    raise