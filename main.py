# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importaciones de Configuración y Servicios
from app.core.config import settings
#from app.services.ai_content_generator import init_gemini_model # Para texto
#from app.services.ai_image_generator import init_image_generation_model # Para imagen

# Importaciones de Routers
from app.api.v1.routers import posts as posts_router
from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import ai_router as ai_content_router # Renombrado para claridad si es necesario
from app.api.v1.routers import organization_settings_router
from app.api.v1.routers import profiles_router

# 1. Crear la instancia de la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

# 2. Configurar Eventos de Ciclo de Vida (startup)
@app.on_event("startup")
async def startup_event():
    print("INFO: Iniciando aplicación FastAPI...")
    # Ya no llamamos a genai.configure() aquí.
    # Solo podemos loguear si la key está presente en nuestra configuración.
    if settings.GOOGLE_API_KEY and \
       settings.GOOGLE_API_KEY.strip() and \
       settings.GOOGLE_API_KEY.lower() not in ["tu_nueva_api_key_real_y_secreta", "no_key_default_should_fail_if_not_set", ""]:
        print(f"INFO startup: GOOGLE_API_KEY está presente en la configuración de la aplicación (primeros 5 chars: {settings.GOOGLE_API_KEY[:5]}...). Se espera que la librería 'google-generativeai' la use automáticamente.")
    else:
        print("WARN startup: GOOGLE_API_KEY no está configurada en la aplicación. La funcionalidad de Gemini dependerá de que la librería la encuentre de otra forma o fallará.")


# 3. Configurar Middlewares (como CORS)
origins = [
    "http://localhost:5173",
    "https://socialmediafe.onrender.com",
    "https://socialmediabe-3o19.onrender.com", # Asegúrate que sea el dominio correcto
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
    ai_content_router.router, # Usando el nombre importado ai_content_router
    prefix=f"{settings.API_V1_STR}/ai",
    tags=["AI Content Generation"] # Este tag agrupa todos los endpoints de IA
)
app.include_router(
    organization_settings_router.router,
    prefix=f"{settings.API_V1_STR}/organization-settings",
    tags=["Organization Settings"]
)
app.include_router(
    profiles_router.router,
    prefix=f"{settings.API_V1_STR}/profiles",
    tags=["Profiles"]
)

# 5. Endpoints Raíz o de Healthcheck (Opcional)
@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

# Para ejecutar con Uvicorn desde la terminal (en la raíz del proyecto):
# uvicorn main:app --reload --host 0.0.0.0 --port 8000