# app/models/connection_models.py

from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

# --------------------------------------------------------------------------- #
# ENUMS
# --------------------------------------------------------------------------- #

# Este Enum mapea directamente el tipo 'social_connection_status' de PostgreSQL.
# Nos proporciona type safety y autocompletado en el backend.
class ConnectionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REQUIRES_REAUTH = "REQUIRES_REAUTH"
    ERROR = "ERROR"

# --------------------------------------------------------------------------- #
# MODELOS DE PETICIÓN Y RESPUESTA
# --------------------------------------------------------------------------- #

class AuthorizationURLResponse(BaseModel):
    """
    Modelo para la respuesta que contiene la URL de autorización de OAuth.
    """
    authorization_url: str


class ConnectionResponse(BaseModel):
    """
    Este es el modelo que devolveremos al frontend al listar las conexiones.
    Es un subconjunto seguro de los datos de la tabla, excluyendo tokens.
    """
    id: UUID
    platform: str
    platform_account_name: str
    platform_account_avatar_url: Optional[str] = None
    status: ConnectionStatusEnum
    created_at: datetime
    updated_at: datetime

    # Configuración para permitir que Pydantic mapee desde objetos de DB
    # y para asegurar que los Enums se serialicen como sus valores (strings).
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

# --------------------------------------------------------------------------- #
# MODELOS DE OAUTH Y ESTADO
# --------------------------------------------------------------------------- #

class OAuthState(BaseModel):
    state: str
    provider: str
    code_verifier: str
    payload: Optional[Dict[str, Any]] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)    