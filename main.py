# main.py
# VERSIÓN FINAL Y COMPLETA - REVISADA Y CORREGIDA POR ELI

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    logging.info("--- SETTINGS CARGADOS CORRECTAMENTE ---")
    print("\n--- RUTAS REGISTRADAS EN LA APLICACIÓN ---")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"Path: {route.path}, Métodos: {route.methods}, Nombre: {route.name}")
        elif hasattr(route, "path_regex"):
            print(f"Path Regex: {route.path_regex}")
    print("------------------------------------------\n")

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "https://5173-gastonhorva-socialmedia-ywmk3dpe1rb.ws-us120.gitpod.io",
    "http://127.0.0.1:5173",
    "https://socialmediafe.onrender.com",
    "http://192.168.0.97:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# El SessionMiddleware se puede eliminar si no se usa explícitamente en los endpoints
# Por ahora lo mantenemos por si es una dependencia implícita de Authlib.
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32)
)

# --- REGISTRO DE ROUTERS - VERSIÓN CORREGIDA ---
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

@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}