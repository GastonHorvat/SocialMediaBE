# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import posts as posts_router # Renombrado para claridad
from app.core.config import settings
from app.api.v1.routers import auth as auth_router 

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
    "http://192.168.0.97:5173",
    # Puedes añadir más orígenes si es necesario
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

app.include_router(
    posts_router.router, 
    prefix=f"{settings.API_V1_STR}/posts", 
    tags=["Posts"]
)

app.include_router(                                # <<< 2. INCLUIR el nuevo router
    auth_router.router,
    prefix=f"{settings.API_V1_STR}/auth",          # URL base para este router: /api/v1/auth
    tags=["Authentication"]                        # Nueva tag para agrupar en /docs
)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to SocialMediaBE FastAPI!"}

# Opcional: añadir más endpoints de healthcheck, etc.

# Para ejecutar con Uvicorn desde la terminal (en la raíz de socialmediabe/):
# uvicorn main:app --reload