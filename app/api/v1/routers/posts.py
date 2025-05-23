# app/api/v1/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from enum import Enum
import pytz

from app.models.post_models import PostCreate, PostUpdate, PostResponse
from app.db.supabase_client import get_supabase_client, Client
from app.api.v1.dependencies.auth import get_current_user, TokenData

class DeletedFilterEnum(str, Enum):
    not_deleted = "not_deleted"
    deleted = "deleted"
    all = "all"

router = APIRouter()

@router.get(
    "/",
    response_model=List[PostResponse],
    summary="Obtener Lista de Posts (con filtros avanzados)",
    description="Devuelve una lista de posts del usuario autenticado dentro de su organización, con opciones para filtrar.",
    tags=["Posts"],
)
async def get_posts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado (ej. draft, approved)"),
    social_network: Optional[str] = Query(None, description="Filtrar por red social"),
    content_type: Optional[str] = Query(None, description="Filtrar por tipo de contenido"),
    date_from: Optional[date] = Query(None, description="Fecha desde (para created_at o scheduled_at)"),
    date_to: Optional[date] = Query(None, description="Fecha hasta (para created_at o scheduled_at)"),
    limit: int = Query(20, ge=1, le=100, description="Número de posts a devolver"),
    offset: int = Query(0, ge=0, description="Número de posts a saltar para paginación"),
    deleted_filter: DeletedFilterEnum = Query(
        DeletedFilterEnum.not_deleted,
        description="Filtrar posts por estado de borrado: "
                    "'not_deleted' (solo activos), "
                    "'deleted' (solo borrados), "
                    "'all' (todos)."
    ),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    print(f"DEBUG get_posts: current_user.user_id='{current_user.user_id}', current_user.organization_id='{current_user.organization_id}', current_user.role='{current_user.role}'") # Añade esto
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id # Puede ser None
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)

        query = supabase.table("posts").select("*").eq("author_user_id", author_id_str)

        if org_id_uuid:
            query = query.eq("organization_id", str(org_id_uuid))
        else:
            # Si el usuario no tiene una organización activa, no debería ver ningún post.
            # Opcionalmente, podrías lanzar una HTTPException aquí.
            print(f"WARN: Usuario {author_id_str} sin organization_id activa, devolviendo lista vacía para get_posts.")
            return []

        if deleted_filter == DeletedFilterEnum.not_deleted:
            query = query.is_("deleted_at", None)
        elif deleted_filter == DeletedFilterEnum.deleted:
            query = query.not_.is_("deleted_at", None)
        # Para 'all', no se aplica filtro de deleted_at.

        if status_filter:
            query = query.eq("status", status_filter)
        if social_network:
            query = query.eq("social_network", social_network)
        if content_type:
            query = query.eq("content_type", content_type)
        if date_from:
            query = query.gte("created_at", str(date_from))
        if date_to:
            query = query.lte("created_at", str(date_to))

        query = query.order("created_at", desc=True).limit(limit).offset(offset)
        response = query.execute()

        posts_data = response.data
        if posts_data:
            return [PostResponse.model_validate(item) for item in posts_data]
        else:
            return []

    except Exception as e:
        print(f"Error fetching posts for user {author_id_str} in org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al obtener los posts. {str(e)}"
        )

@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un Nuevo Post",
    description="Crea un nuevo post asociado al usuario autenticado y su organización.",
    tags=["Posts"]
)
async def create_post(
    post_data: PostCreate,
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id

        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede crear el post: el usuario no está asociado a una organización activa."
            )

        new_post_dict = post_data.model_dump(exclude_unset=True)
        new_post_dict["author_user_id"] = author_id_str
        new_post_dict["organization_id"] = str(org_id_uuid) # Seguro porque ya verificamos

        query = supabase.table("posts").insert(new_post_dict).select().single().execute()
        
        created_post_data = query.data
        if not created_post_data:
            # Esto podría ser un error de base de datos si la inserción falló silenciosamente
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear el post o no se obtuvieron los datos del post creado."
            )
        return PostResponse.model_validate(created_post_data)

    except HTTPException as http_exc: # Re-lanzar HTTPExceptions que ya manejamos (como el 400)
        raise http_exc
    except Exception as e:
        print(f"Error creando post para user {author_id_str} en org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al crear el post: {str(e)}"
        )

@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Obtener un Post Específico",
    description="Recupera un post por ID, si pertenece al usuario y su organización.",
    tags=["Posts"]
)
async def get_post_by_id(
    post_id: UUID = Path(..., description="El ID del post a recuperar"),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id
        
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            # Si no hay organización, el post no puede pertenecer al usuario en una organización.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado o acceso denegado (usuario sin organización activa)."
            )

        query_builder = (
            supabase.table("posts")
            .select("*")
            .eq("id", str(post_id))
            .eq("author_user_id", author_id_str)
            .eq("organization_id", str(org_id_uuid)) # Seguro porque org_id_uuid está validado
            .is_("deleted_at", None)
            .single()
        )
        
        response = query_builder.execute()
        post_data = response.data

        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario/organización, o ha sido eliminado."
            )
        return PostResponse.model_validate(post_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error obteniendo post {post_id} para user {author_id_str} en org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al obtener el post: {str(e)}"
        )

@router.patch(
    "/{post_id}", 
    response_model=PostResponse,
    summary="Actualizar Parcialmente un Post",
    description="Actualiza campos de un post existente. No permite cambiar autor ni organización.",
    tags=["Posts"]
)
async def update_post_partial(
    post_update_data: PostUpdate,
    post_id: UUID = Path(..., description="El ID del post a actualizar"),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"

    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id

        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, # O 403
                detail=f"No se puede actualizar el post {post_id}: usuario sin organización activa."
            )

        update_data_dict = post_update_data.model_dump(exclude_unset=True)
        if not update_data_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar."
            )
        
        # Considerar añadir updated_at si la DB no lo maneja con triggers
        # update_data_dict["updated_at"] = datetime.now(pytz.utc).isoformat()

        query_builder = (
            supabase.table("posts")
            .update(update_data_dict)
            .eq("id", str(post_id))
            .eq("author_user_id", author_id_str)
            .eq("organization_id", str(org_id_uuid)) # Seguro
            .is_("deleted_at", None) # No se pueden modificar posts borrados lógicamente
            .select()
            .single()
        )
        
        response = query_builder.execute()
        updated_post_data = response.data

        if not updated_post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario/organización, o está eliminado."
            )
        return PostResponse.model_validate(updated_post_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error actualizando post {post_id} para user {author_id_str} en org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al actualizar el post: {str(e)}"
        )

@router.delete(
    "/{post_id}",
    response_model=PostResponse,
    summary="Borrar Lógicamente un Post",
    description="Marca un post como eliminado (soft delete).",
    tags=["Posts"]
)
async def soft_delete_post(
    post_id: UUID = Path(..., description="El ID del post a marcar como eliminado"),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    author_id_str: Optional[str] = None
    org_id_uuid: Optional[UUID] = None
    org_id_for_log: str = "None"
    
    try:
        author_id_str = str(current_user.user_id)
        org_id_uuid = current_user.organization_id
        
        if org_id_uuid:
            org_id_for_log = str(org_id_uuid)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, # O 403
                detail=f"No se puede eliminar el post {post_id}: usuario sin organización activa."
            )

        now_utc = datetime.now(pytz.utc)
        update_payload = {
            "deleted_at": now_utc.isoformat(),
            "status": "deleted" 
            # "updated_at": now_utc.isoformat() # Si la DB no lo hace automáticamente
        }

        query_builder = (
            supabase.table("posts")
            .update(update_payload)
            .eq("id", str(post_id))
            .eq("author_user_id", author_id_str)
            .eq("organization_id", str(org_id_uuid)) # Seguro
            .is_("deleted_at", None) # Solo borrar si no está ya borrado
            .select()
            .single()
        )
        
        response = query_builder.execute()
        deleted_post_data = response.data

        if not deleted_post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario/organización, o ya estaba eliminado."
            )
        return PostResponse.model_validate(deleted_post_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error soft-deleting post {post_id} para user {author_id_str} en org {org_id_for_log}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al marcar el post como eliminado: {str(e)}"
        )