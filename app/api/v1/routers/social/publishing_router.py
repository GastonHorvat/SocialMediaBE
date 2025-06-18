# app/api/v1/routers/social/publishing_router.py
# VERSIÓN FINAL - ALINEADO CON LA ARQUITECTURA SYNC/ASYNC CORRECTA

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

# Dependencias
from app.services.social.publishing_service import publishing_service
from app.api.v1.dependencies.resources import get_valid_connection_for_user

router = APIRouter()

@router.post(
    "/posts/{post_id}/connections/{connection_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Publish a Post to a Social Connection (Secure)"
)
async def publish_post_to_social_media(
    post_id: UUID,
    # La dependencia se encarga de obtener la conexión y verificar los permisos.
    connection: dict = Depends(get_valid_connection_for_user),
):
    """
    Publica un post existente en una plataforma social a través de una conexión específica.
    
    Este endpoint está protegido y verifica que el usuario pertenezca a la organización
    de la conexión antes de intentar cualquier acción.
    """
    try:
        # La llamada a `publishing_service.publish_post` ES ASÍNCRONA, por lo que
        # 'await' es correcto y necesario aquí.
        publication_result = await publishing_service.publish_post(
            post_id=post_id,
            connection_id=UUID(connection['id']) # Buena práctica: asegurar el tipo UUID
        )
        return publication_result
        
    except ValueError as e:
        # Errores de validación (ej. post o conexión no encontrados).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotImplementedError as e:
        # Plataforma no soportada por el dispatcher.
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except Exception as e:
        # Errores genéricos (API de la plataforma, errores de red, etc.).
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Ocurrió un error durante la publicación: {e}")