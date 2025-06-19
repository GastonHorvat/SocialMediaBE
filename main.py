# main.py
# Versión final, SIN el router de callback separado.

import secrets
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

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

# ... (Bloque de configuración de logging sin cambios) ...
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

# 3. Creación de la Instancia de la Aplicación
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

# 4. Configuración de Eventos de Ciclo de Vida (startup)
@app.on_event("startup")
async def startup_event():
    # ... (lógica de startup sin cambios) ...
    logging.info("--- SETTINGS CARGADOS CORRECTAMENTE ---")
    # ...
    print("\n--- RUTAS REGISTRADAS EN LA APLICACIÓN ---")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"Path: {route.path}, Métodos: {route.methods}, Nombre: {route.name}")
        elif hasattr(route, "path_regex"):
            print(f"Path Regex: {route.path_regex}")
    print("------------------------------------------\n")

# 5. Configuración de Middlewares (CORS, Sesión)
# ... (lógica de middlewares sin cambios) ...
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
# ...

# 6. Registro de Routers
# Routers de la API principal, todos bajo el prefijo /api/v1
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