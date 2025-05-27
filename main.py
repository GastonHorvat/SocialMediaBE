# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Solo necesitas esta importación para CORS

# Importaciones de Configuración y Servicios
from app.core.config import settings
from app.services.ai_content_generator import init_gemini_model

# Importaciones de Routers (una sola vez y consistentemente)
from app.api.v1.routers import posts as posts_router 
from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import ai_router 
from app.api.v1.routers import organization_settings_router
from app.api.v1.routers import profiles_router # <--- Ya tienes esta importación, ¡genial!


# 1. Crear la instancia de la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

# 2. Configurar Eventos de Ciclo de Vida (ej. startup)
@app.on_event("startup")
async def startup_event():
    print("INFO: Iniciando aplicación FastAPI...")
    if (settings.GOOGLE_API_KEY and 
        settings.GOOGLE_API_KEY.strip() and
        settings.GOOGLE_API_KEY != "TU_NUEVA_API_KEY_REAL_Y_SECRETA" and
        settings.GOOGLE_API_KEY != "NO_KEY_DEFAULT_SHOULD_FAIL_IF_NOT_SET"):
        print(f"INFO: Inicializando modelo Gemini con API Key: {settings.GOOGLE_API_KEY[:5]}...")
        try:
            init_gemini_model(settings.GOOGLE_API_KEY)
        except Exception as e:
            print(f"ERROR CRITICO: Falló la inicialización del modelo Gemini durante el startup: {e}")
    else:
        print("WARN: GOOGLE_API_KEY no está configurada o es un valor placeholder. La funcionalidad de Gemini no estará disponible.")

# 3. Configurar Middlewares (como CORS)
origins = [
    "http://localhost:5173",
    "https://socialmediafe.onrender.com",
    "https://socialmediabe-3o19.onrender.com",
    "http://192.168.0.97:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Registrar Routers
app.include_router(
    auth_router.router, 
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"] 
)
app.include_router(
    posts_router.router, 
    prefix=f"{settings.API_V1_STR}/posts",
    tags=["Posts"]
)
app.include_router(
    ai_router.router, 
    prefix=f"{settings.API_V1_STR}/ai",
    tags=["AI Content Generation"]
)
app.include_router(
    organization_settings_router.router, 
    prefix=f"{settings.API_V1_STR}/organization-settings", 
    tags=["Organization Settings"]
)
# --- AÑADIR ESTE BLOQUE PARA EL ROUTER DE PERFILES ---
app.include_router(
    profiles_router.router, # Usa el objeto router del módulo importado
    prefix=f"{settings.API_V1_STR}/profiles", # URL base: /api/v1/profiles
    tags=["Profiles"] # Tag para agrupar en /docs
)
# --- FIN DEL BLOQUE AÑADIDO ---

# 5. Endpoints Raíz o de Healthcheck (Opcional)
@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

# Para ejecutar con Uvicorn desde la terminal (en la raíz del proyecto):
# uvicorn main:app --reload