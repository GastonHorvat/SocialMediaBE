# app/api/v1/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from uuid import UUID
from pydantic import BaseModel
from app.core.config import settings

oauth2_scheme = HTTPBearer()

class TokenData(BaseModel):
    user_id: UUID

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> TokenData:
    # print(f"AUTH_DEBUG: Entrando a get_current_user. Objeto token recibido: {token}") # Opcional
    # if token:
    #     print(f"AUTH_DEBUG: token.scheme: {token.scheme}, token.credentials (primeros 10): {token.credentials[:10] if token.credentials else None}...") # Opcional

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None or token.scheme.lower() != "bearer":
        # print(f"AUTH_DEBUG: Token es None o el scheme no es 'bearer'. Scheme: {token.scheme if token else 'Token es None'}") # Opcional
        raise credentials_exception
    
    jwt_token = token.credentials

    try:
        secret_to_use = settings.SUPABASE_JWT_SECRET
        # print(f"AUTH_DEBUG: Usando secreto (len {len(secret_to_use) if secret_to_use else 'None'})") # Opcional
        # print(f"AUTH_DEBUG: Intentando decodificar token (primeros 30): {jwt_token[:30] if jwt_token else 'Token vacío'}...") # Opcional

        payload = jwt.decode(
            jwt_token, 
            secret_to_use,
            algorithms=["HS256"], 
            audience="authenticated" 
        )
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            # print(f"AUTH_DEBUG: 'sub' (user_id) no encontrado en el payload: {payload}") # Opcional
            raise credentials_exception
        
        # print(f"AUTH_DEBUG: User ID extraído: {user_id_str}") # Opcional
        return TokenData(user_id=UUID(user_id_str))

    except JWTError as e:
        # print(f"AUTH_DEBUG: JWTError específico: {e}") # Mantén este si quieres ver errores JWT futuros
        raise credentials_exception
    except Exception as e:
        # print(f"AUTH_DEBUG: Excepción inesperada en get_current_user: {e}") # Opcional
        raise credentials_exception