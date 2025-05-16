from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Asegúrate que esta línea esté

app = FastAPI()

# Lista de orígenes permitidos
origins = [
    "http://localhost:5173",  # Para tu desarrollo local del FE
    "https://socialmediafe.onrender.com", # La URL de tu FE desplegado en Render (cuando lo tengas y sepas la URL exacta)
    # Puedes añadir la URL de tu BE aquí también si quieres ser explícito, aunque no siempre es necesario
    # "https://socialmediabe-3o19.onrender.com"
]

# Añadir el middleware CORS a tu aplicación FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # crucial: pasar la lista de orígenes
    allow_credentials=True, # permite cookies si las usas
    allow_methods=["*"],    # permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],    # permite todos los encabezados
)

@app.get("/")
async def root():
    return {"message": "Hello from SocialMediaBE FastAPI!"}

# Si tienes más endpoints, irán después de la configuración del middleware