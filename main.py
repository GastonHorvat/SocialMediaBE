from fastapi import FastAPI

app = FastAPI() # Esta es la instancia 'app' que Uvicorn buscará

@app.get("/") # Una ruta de ejemplo para probar
async def root():
    return {"message": "Hello from SocialMediaBE FastAPI!"}

# No necesitas el bloque if __name__ == "__main__": uvicorn.run(...)
# porque Render ejecutará Uvicorn directamente con el Start Command.