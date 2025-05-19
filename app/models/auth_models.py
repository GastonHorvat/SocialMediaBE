# app/models/auth_models.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class TokenRequestForm(BaseModel):
    email: EmailStr 
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    # user_id: Optional[str] = None # Opcional si quieres devolverlo