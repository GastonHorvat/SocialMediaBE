# app/core/config.py
import os
# from dotenv import load_dotenv, find_dotenv # <--- QUITAR ESTAS LÍNEAS
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# --- YA NO LLAMAMOS A load_dotenv() EXPLÍCITAMENTE AQUÍ ---
# dotenv_path = find_dotenv(...)
# load_dotenv(...)

# --- DEFINICIÓN DE SETTINGS CON PYDANTIC ---
class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Media BE"
    API_V1_STR: str = "/api/v1"

    # Supabase - Obligatorias
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Google Gemini - Obligatoria
    GOOGLE_API_KEY: str
    
    # OpenAI - Clave API - Obligatoria
    OPENAI_API_KEY: str 

    # Configuraciones para Imágenes de OpenAI - Leídas desde .env
    # Pydantic fallará al inicio si no están en .env
    OPENAI_IMAGE_MODEL: str
    OPENAI_IMAGE_SIZE: str
    OPENAI_IMAGE_QUALITY: str

    model_config = SettingsConfigDict(
        env_file=".env", # <--- Especificar el nombre del archivo .env directamente
                         # pydantic-settings lo buscará en el directorio actual y superiores.
        env_file_encoding='utf-8',
        extra='ignore',
        # case_sensitive=False, # Default, las variables de entorno son case-insensitive en muchos sistemas
                               # pero las claves en el archivo .env deben coincidir.
    )

# --- INSTANCIACIÓN ---
try:
    settings = Settings()
    
    print("--- SETTINGS CARGADOS POR PYDANTIC (confiando en pydantic-settings para .env) ---")
    print(f"PROJECT_NAME: {settings.PROJECT_NAME}")
    print(f"OPENAI_API_KEY: {'SET' if settings.OPENAI_API_KEY else 'NOT SET'}") # Para verificar que carga algo
    print(f"OPENAI_IMAGE_MODEL: {settings.OPENAI_IMAGE_MODEL}")
    print(f"OPENAI_IMAGE_SIZE: {settings.OPENAI_IMAGE_SIZE}")
    print(f"OPENAI_IMAGE_QUALITY: {settings.OPENAI_IMAGE_QUALITY}")
    print(f"-----------------------------------")

except Exception as e:
    print(f"!!! ERROR CRÍTICO AL CARGAR SETTINGS CON PYDANTIC (config.py): {type(e).__name__} - {e}")
    print("!!! Verifique que su archivo .env exista en la raíz del proyecto y contenga TODAS las variables requeridas.")
    raise