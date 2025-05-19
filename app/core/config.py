# app/core/config.py
import os
from dotenv import load_dotenv, find_dotenv # Importar find_dotenv

# Cargar .env y obtener la ruta del archivo .env que se usó
dotenv_path = find_dotenv(raise_error_if_not_found=False) # No lanzar error si no se encuentra
print(f"CONFIG_DEBUG: Intentando cargar .env desde: {dotenv_path}")
loaded = load_dotenv(dotenv_path=dotenv_path, override=True) # override=True para asegurar que los valores del .env se usen
print(f"CONFIG_DEBUG: load_dotenv() cargó variables: {loaded}")


# Imprimir el valor crudo directamente de os.environ después de load_dotenv
raw_secret_from_os_environ = os.environ.get("SUPABASE_JWT_SECRET")
print(f"--- DEBUG DIRECTO DE OS.ENVIRON ---")
if raw_secret_from_os_environ is not None:
    print(f"os.environ['SUPABASE_JWT_SECRET'] (repr): {repr(raw_secret_from_os_environ)}")
    print(f"os.environ['SUPABASE_JWT_SECRET'] (len): {len(raw_secret_from_os_environ)}")
else:
    print("SUPABASE_JWT_SECRET no encontrado en os.environ después de load_dotenv")
print(f"-----------------------------------")

# ... (resto de tu clase Settings y la instanciación de settings como la tenías
#      con el print de DEBUG: SUPABASE_JWT_SECRET (completo): '...'
#      y el print de la longitud)
# Por ejemplo:
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str

    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=dotenv_path if dotenv_path else ".env", # Usar la ruta detectada o default
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
try:
    settings = Settings()
    print("--- SETTINGS LOADED ---")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL[:20] if settings.SUPABASE_URL else 'NO CARGADA'}")
    print(f"SUPABASE_KEY (primeros 10): {settings.SUPABASE_KEY[:10] if settings.SUPABASE_KEY else 'NO CARGADA'}...")
    
    if settings.SUPABASE_JWT_SECRET:
        print(f"DEBUG: settings.SUPABASE_JWT_SECRET (completo): '{settings.SUPABASE_JWT_SECRET}'")
        print(f"DEBUG: settings.SUPABASE_JWT_SECRET (len): {len(settings.SUPABASE_JWT_SECRET)}")
    else:
        print("DEBUG: settings.SUPABASE_JWT_SECRET: NO CARGADA O VACÍA")
    print(f"-----------------------")
except Exception as e:
    print(f"!!! ERROR AL CARGAR SETTINGS: {e}")
    raise