# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import posts as posts_router # Renombrado para claridad
from app.core.config import settings

app = FastAPI(
    title="SocialMediaBE API",
    description="Backend para la gestión de contenido en redes sociales.",
    version="0.1.0"
)

# Configuración de CORS (como la tenías, pero adaptada)
# Lista de orígenes permitidos
origins = [
    "http://localhost:5173",  # Para tu desarrollo local del FE
    "https://socialmediafe.onrender.com",  # La URL de tu FE desplegado
    "https://socialmediabe-3o19.onrender.com" # Tu propio BE
    # Puedes añadir más orígenes si es necesario
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# Incluir routers de la API
app.include_router(posts_router.router, prefix=settings.API_V1_STR, tags=["Posts"]) # tags aquí son para la sección general

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to SocialMediaBE FastAPI!"}

# Opcional: añadir más endpoints de healthcheck, etc.

# Para ejecutar con Uvicorn desde la terminal (en la raíz de socialmediabe/):
# uvicorn main:app --reload