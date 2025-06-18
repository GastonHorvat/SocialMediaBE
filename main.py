# main.py
# VERSIÓN FINAL CON LOGGING CONFIGURADO

# 1. Importaciones de Librerías Estándar y de Terceros
import secrets
import logging
import sys # <-- Importación necesaria para el handler de logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# 2. Importaciones de la Aplicación
from app.core.config import settings
from app.api.v1.routers import (
    posts as posts_router,
    auth as auth_router,
    ai_router,
    organization_settings_router,
    profiles_router
)
from app.api.v1.routers.social import (
    connections_router,
    publishing_router
)

# --- INICIO DEL BLOQUE DE CONFIGURACIÓN DE LOGGING ---
# Esta configuración se aplica a toda la aplicación para asegurar que
# los mensajes de nivel INFO sean visibles en la consola.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
# --- FIN DEL BLOQUE DE CONFIGURACIÓN DE LOGGING ---

# 3. Creación de la Instancia de la Aplicación
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

# 4. Configuración de Eventos de Ciclo de Vida (startup)
@app.on_event("startup")
async def startup_event():
    # Usamos el logger que ahora está configurado globalmente
    logging.info("--- SETTINGS CARGADOS CORRECTAMENTE ---")
    logging.info(f"PROJECT_NAME: {settings.PROJECT_NAME}")
    logging.info(f"LINKEDIN_CLIENT_ID: {'SET' if settings.LINKEDIN_CLIENT_ID else 'NOT SET'}")
    logging.info(f"TOKENS_ENCRYPTION_KEY: {'SET' if settings.TOKENS_ENCRYPTION_KEY else 'NOT SET'}")
    logging.info("-----------------------------------")
    
    # El bloque de depuración de rutas se mantiene igual
    print("\n--- RUTAS REGISTRADAS EN LA APLICACIÓN ---")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"Path: {route.path}, Métodos: {route.methods}, Nombre: {route.name}")
        elif hasattr(route, "path_regex"):
            print(f"Path Regex: {route.path_regex}")
    print("------------------------------------------\n")

# 5. Configuración de Middlewares (CORS, Sesión)
# El orden es importante: CORS primero para que maneje las peticiones OPTIONS
# y añada las cabeceras a las respuestas de otros middlewares.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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

SESSION_SECRET_KEY = settings.SESSION_SECRET_KEY if hasattr(settings, 'SESSION_SECRET_KEY') and settings.SESSION_SECRET_KEY else secrets.token_hex(32)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    https_only=not settings.DEBUG,
    same_site="lax"
)

# 6. Registro de Routers
app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(posts_router.router, prefix=f"{settings.API_V1_STR}/posts", tags=["Posts"])
app.include_router(ai_router.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI"])
app.include_router(organization_settings_router.router, prefix=f"{settings.API_V1_STR}/organization-settings", tags=["Organization Settings"])
app.include_router(profiles_router.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["Profiles"])

app.include_router(
    connections_router.router,
    prefix=f"{settings.API_V1_STR}/connections",
    tags=["Social Connections"]
)
app.include_router(
    publishing_router.router,
    prefix=f"{settings.API_V1_STR}/publishing",
    tags=["Social Publishing"]
)

# 7. Endpoint Raíz
@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}