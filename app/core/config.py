# app/core/config.py
import os
from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional # Asegúrate de tener Optional si alguna variable podría no estar

# --- CARGA DE .ENV ---
# Cargar .env y obtener la ruta del archivo .env que se usó
# find_dotenv buscará .env subiendo en el árbol de directorios desde el script actual.
# Esto es útil si ejecutas scripts desde subdirectorios.
# Si config.py está en app/core/ y .env en la raíz del proyecto, debería encontrarlo.
dotenv_path = find_dotenv(raise_error_if_not_found=False, usecwd=True) # usecwd=True para buscar también en el dir actual
print(f"CONFIG_DEBUG: `find_dotenv()` encontró .env en: {dotenv_path if dotenv_path else 'No encontrado, se usará .env por defecto si existe'}")

# Cargar las variables del .env encontrado (o el por defecto si no se especifica path)
# override=True asegura que los valores del .env se usen incluso si ya existen en el entorno.
loaded = load_dotenv(dotenv_path=dotenv_path, override=True)
print(f"CONFIG_DEBUG: `load_dotenv()` intentó cargar desde '{dotenv_path if dotenv_path else '.env por defecto'}'. Variables cargadas: {loaded}")

# --- DEBUG DE VARIABLES DE ENTORNO CRUDAS (DESPUÉS DE LOAD_DOTENV) ---
print(f"--- DEBUG CRUDO DESDE OS.ENVIRON (POST-LOAD_DOTENV) ---")
env_vars_to_check = ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_JWT_SECRET", "GOOGLE_API_KEY"]
for var_name in env_vars_to_check:
    value = os.environ.get(var_name)
    if value is not None:
        print(f"os.environ['{var_name}'] (repr): {repr(value)}")
        if var_name in ["SUPABASE_KEY", "GOOGLE_API_KEY"]: # No mostrar secretos completos
            print(f"os.environ['{var_name}'] (primeros 5): {value[:5]}...")
        print(f"os.environ['{var_name}'] (len): {len(value)}")
    else:
        print(f"{var_name} NO encontrado en os.environ")
print(f"------------------------------------------------------")


# --- DEFINICIÓN DE SETTINGS CON PYDANTIC ---
class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Media BE" # Valor por defecto si no está en .env
    API_V1_STR: str = "/api/v1"     # Valor por defecto

    # Supabase - Estas deberían estar en tu .env
    SUPABASE_URL: str
    SUPABASE_KEY: str # Esta es la anon key, generalmente
    SUPABASE_JWT_SECRET: str

    # Google Gemini - Esta debería estar en tu .env
    # Si no se proporciona en .env, Pydantic lanzará un error de validación
    # a menos que le des un valor por defecto aquí (lo cual no es ideal para API keys).
    # Si quieres que falle si no está, simplemente no le pongas default.
    # Si quieres un default que indique que no está seteada, puedes usar Optional[str] = None
    # pero luego tu código debe manejar el caso de None.
    # Para una API key, es mejor que falle si no está.
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str 

    # Configuración de Pydantic para leer desde .env
    model_config = SettingsConfigDict(
        env_file=dotenv_path if dotenv_path else ".env", # Usar la ruta detectada o el default ".env"
        env_file_encoding='utf-8',
        # case_sensitive=True, # Descomenta si tus variables de entorno son sensibles a mayúsculas/minúsculas
        extra='ignore' # Ignorar variables extra en el .env que no estén en el modelo Settings
    )

# --- INSTANCIACIÓN Y DEBUG DE SETTINGS ---
try:
    settings = Settings()
    print("--- SETTINGS CARGADOS POR PYDANTIC ---")
    print(f"PROJECT_NAME: {settings.PROJECT_NAME}")
    print(f"API_V1_STR: {settings.API_V1_STR}")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL[:25] if settings.SUPABASE_URL else 'NO CARGADA'}...") # Acortado para no llenar log
    print(f"SUPABASE_KEY (primeros 10): {settings.SUPABASE_KEY[:10] if settings.SUPABASE_KEY else 'NO CARGADA'}...")
    
    if settings.SUPABASE_JWT_SECRET:
        # No imprimir el secreto completo en logs de producción, solo para depuración local.
        # print(f"DEBUG: settings.SUPABASE_JWT_SECRET (completo): '{settings.SUPABASE_JWT_SECRET}'")
        print(f"settings.SUPABASE_JWT_SECRET (len): {len(settings.SUPABASE_JWT_SECRET)}")
    else:
        print("settings.SUPABASE_JWT_SECRET: NO CARGADA O VACÍA")

    if settings.GOOGLE_API_KEY:
        print(f"settings.GOOGLE_API_KEY (primeros 5): {settings.GOOGLE_API_KEY[:5]}...")
        print(f"settings.GOOGLE_API_KEY (len): {len(settings.GOOGLE_API_KEY)}")
    else:
        # Pydantic debería haber fallado si GOOGLE_API_KEY no tiene default y no está en .env
        print("settings.GOOGLE_API_KEY: NO CARGADA O VACÍA (esto no debería pasar si es requerida sin default)")
    print(f"-----------------------------------")

except Exception as e:
    print(f"!!! ERROR CRÍTICO AL CARGAR SETTINGS CON PYDANTIC: {e}")
    print("!!! LA APLICACIÓN PROBABLEMENTE NO FUNCIONARÁ CORRECTAMENTE SIN SETTINGS.")
    # Considera si quieres que la aplicación se detenga aquí si los settings son críticos
    # import sys
    # sys.exit(1)
    raise # Re-lanzar la excepción para que FastAPI la maneje o detenga el inicio