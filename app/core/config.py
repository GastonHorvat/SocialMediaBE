# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# --- DEFINICIÓN DE SETTINGS CON PYDANTIC ---
class Settings(BaseSettings):
    # --- Metadatos del Proyecto ---
    PROJECT_NAME: str = "Social Media BE"
    API_V1_STR: str = "/api/v1"
    # Añadimos un flag de debug para controlar el comportamiento 'secure' de las cookies
    DEBUG: bool = True 
    FRONTEND_URL: str = "http://localhost:5173" # Valor por defecto para desarrollo

    # --- Credenciales de APIs (Obligatorias, leídas del .env) ---
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str 
    
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str
    
    TOKENS_ENCRYPTION_KEY: str

    # --- Configuraciones con Valores por Defecto (si no están en .env) ---
    OPENAI_IMAGE_MODEL: str = "dall-e-3"
    OPENAI_IMAGE_SIZE: str = "1024x1024"
    OPENAI_IMAGE_QUALITY: str = "standard"
        
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

# --- INSTANCIACIÓN ---
try:
    settings = Settings()
    
    # Log de verificación al inicio
    print("--- SETTINGS CARGADOS CORRECTAMENTE ---")
    print(f"PROJECT_NAME: {settings.PROJECT_NAME}")
    print(f"LINKEDIN_CLIENT_ID: {'SET' if settings.LINKEDIN_CLIENT_ID else 'NOT SET'}")
    print(f"TOKENS_ENCRYPTION_KEY: {'SET' if settings.TOKENS_ENCRYPTION_KEY else 'NOT SET'}")
    print("-----------------------------------")

except Exception as e:
    print(f"!!! ERROR CRÍTICO AL CARGAR SETTINGS (config.py): {type(e).__name__} - {e}")
    print("!!! Verifique que su archivo .env exista y contenga TODAS las variables requeridas (SUPABASE_URL, LINKEDIN_CLIENT_ID, etc.).")
    raise