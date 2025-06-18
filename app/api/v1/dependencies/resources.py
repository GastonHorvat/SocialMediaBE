# app/api/v1/dependencies/resources.py

from uuid import UUID
from fastapi import Depends, HTTPException, status

# --- CORRECCIÓN CLAVE: Importamos TokenData desde su ubicación real ---
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.services.social.connections_service import connections_service

async def get_valid_connection_for_user(
    connection_id: UUID,
    current_user: TokenData = Depends(get_current_user) # <-- Usamos el tipo correcto
) -> dict:
    """
    Dependencia de FastAPI para obtener una conexión y verificar la propiedad.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No perteneces a una organización activa."
        )

    connection = await connections_service.get_connection_by_id(connection_id)
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conexión con ID {connection_id} no encontrada."
        )

    if str(connection.get("organization_id")) != str(current_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este recurso de conexión."
        )

    # (Preparación para RBAC omitida por brevedad, la lógica no cambia)
    return connection