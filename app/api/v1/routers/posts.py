# app/api/v1/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime # Importar date
from enum import Enum # Asegúrate que Enum esté importado si defines DeletedFilterEnum aquí
import pytz # Importar pytz para manejar zonas horarias

from app.models.post_models import PostCreate, PostUpdate, PostResponse
from app.db.supabase_client import get_supabase_client, Client
from app.api.v1.dependencies.auth import get_current_user, TokenData 
# Si prefieres la validación SDK: from app.api.v1.dependencies.auth import get_current_user_supabase_sdk as get_current_user

class DeletedFilterEnum(str, Enum): # Definición del Enum
    not_deleted = "not_deleted"
    deleted = "deleted"
    all = "all"

router = APIRouter()

get_posts_examples = {
    "default_active_posts": {
        "summary": "Obtener posts activos (por defecto)",
        "value": {} # deleted_filter usará su default que es DeletedFilterEnum.not_deleted
    },
    "only_deleted_posts": {
        "summary": "Obtener solo posts borrados",
        "value": {
            "deleted_filter": DeletedFilterEnum.deleted.value # Usar el valor del enum
        }
    },
    "all_posts_instagram": {
        "summary": "Obtener todos los posts de Instagram",
        "value": {
            "social_network": "instagram",
            "deleted_filter": DeletedFilterEnum.all.value # Usar el valor del enum
        }
    },
    "drafts_last_week": {
        "summary": "Borradores de la última semana",
        "value": {
            "status_filter": "draft",
            "date_from": "2023-10-20",
            "date_to": "2023-10-27",
            "deleted_filter": DeletedFilterEnum.not_deleted.value # Usar el valor del enum
        }
    },
    "custom_pagination": {
        "summary": "Paginación personalizada",
        "value": {
            "limit": 10,
            "offset": 10,
            "deleted_filter": DeletedFilterEnum.not_deleted.value # Usar el valor del enum
        }
    }
}

@router.get(
    "/", # Asumiendo que el prefix "/posts" está en main.py
    response_model=List[PostResponse],
    summary="Obtener Lista de Posts (con filtros avanzados)",
    description="Devuelve una lista de posts del usuario autenticado, con opciones para filtrar por estado de borrado.",
    tags=["Posts"]
)
async def get_posts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado de la tarea (ej. draft, approved, deleted)"),
    social_network: Optional[str] = Query(None, description="Filtrar por red social"),
    content_type: Optional[str] = Query(None, description="Filtrar por tipo de contenido"),
    date_from: Optional[date] = Query(None, description="Fecha desde (para created_at o scheduled_at)"),
    date_to: Optional[date] = Query(None, description="Fecha hasta (para created_at o scheduled_at)"),
    limit: int = Query(20, ge=1, le=100, description="Número de posts a devolver"),
    offset: int = Query(0, ge=0, description="Número de posts a saltar para paginación"),
    deleted_filter: Optional[str] = Query( # Nuevo parámetro más flexible
        "not_deleted", # Valor por defecto: solo los no borrados
        description="Filtrar posts por estado de borrado: "
                    "'not_deleted' (solo activos, deleted_at IS NULL), "
                    "'deleted' (solo borrados, deleted_at IS NOT NULL), "
                    "'all' (todos, sin importar deleted_at)."
    ),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    try:
        user_id = current_user.user_id
        query = supabase.table("posts").select("*").eq("user_id", str(user_id))

        # Aplicar filtro de borrado lógico
        if deleted_filter == "not_deleted":
            query = query.is_("deleted_at", None)
        elif deleted_filter == "deleted":
            query = query.not_.is_("deleted_at", None) # o query.neq("deleted_at", None) si prefieres - aunque is_not_null es más idiomático
        elif deleted_filter == "all":
            pass # No se aplica filtro por deleted_at
        else:
            # Si se proporciona un valor inválido para deleted_filter, por defecto no traer borrados
            # O podrías lanzar un HTTPException(status.HTTP_400_BAD_REQUEST, detail="Valor inválido para deleted_filter")
            query = query.is_("deleted_at", None)


        # Filtro de status (considerando el filtro de borrado)
        if status_filter:
            # Si el usuario pide específicamente status="deleted", tiene sentido.
            # Si el usuario pide status="draft" y deleted_filter="deleted", no encontrará nada (lo cual es correcto).
            query = query.eq("status", status_filter)
        
        # ... (resto de tus filtros como los tenías: social_network, content_type, date_from, date_to) ...
        if social_network:
            query = query.eq("social_network", social_network)
        if content_type:
            query = query.eq("content_type", content_type)
        if date_from:
            query = query.gte("created_at", str(date_from))
        if date_to:
            query = query.lte("created_at", str(date_to))

        query = query.order("created_at", desc=True)
        query = query.limit(limit).offset(offset)

        response = query.execute()

        if response.data:
            posts = [PostResponse.model_validate(item) for item in response.data]
            return posts
        else:
            return []

    except Exception as e:
        print(f"Error fetching posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al obtener los posts."
        )

@router.delete(
    "/{post_id}", # Asumiendo que el prefix "/posts" está en main.py
    response_model=PostResponse, # Ahora devolveremos el post actualizado
    summary="Borrar Lógicamente un Post (marcar como eliminado)",
    description="Actualiza el campo 'deleted_at' del post para marcarlo como eliminado. Asegura que pertenezca al usuario autenticado.",
    tags=["Posts"]
)
async def soft_delete_post( # Renombrado para claridad
    post_id: UUID = Path(..., description="El ID del post a marcar como eliminado"),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    user_id = current_user.user_id
    # Obtener la fecha y hora actual con zona horaria UTC
    # Es importante ser consistente con las zonas horarias en la base de datos
    now_utc = datetime.now(pytz.utc) 

    try:
        # Actualizar el post para establecer deleted_at y opcionalmente cambiar status
        update_data = {
            "deleted_at": now_utc.isoformat(), # Guardar como string ISO 8601
            "status": "deleted" # Opcional: puedes tener un status específico
            # "updated_at": now_utc.isoformat() # Supabase puede manejar esto con un trigger
        }
        
        # Usamos el método update() y especificamos que devuelva el registro actualizado con 'returning="representation"'
        # (en supabase-py >v2, esto podría ser .select().single() después del update)
        # Para supabase-py v1.x, `update().execute()` devuelve los datos actualizados si hay `returning`.
        # Para supabase-py v2.x, la sintaxis podría ser un poco diferente para obtener el resultado.
        # Asumamos que tu tabla tiene `updated_at` que se actualiza automáticamente.
        
        # Supabase-py v1.x style
        # query = supabase.table("posts").update(update_data).eq("id", str(post_id)).eq("user_id", str(user_id)).execute()
        
        # Supabase-py v2.x style (más común ahora)
        query = supabase.table("posts").update(update_data).eq("id", str(post_id)).eq("user_id", str(user_id)).select().single().execute()


        if not query.data: # Si no se actualizó nada (no encontrado o no pertenece al usuario)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado o no pertenece al usuario."
            )
        
        # El post actualizado está en query.data
        updated_post_data = query.data
        return PostResponse.model_validate(updated_post_data) # Validar y devolver

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error soft deleting post {post_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al intentar marcar el post como eliminado."
        )
    
@router.post(
    "/", # Asumiendo que el prefix "/posts" está en main.py
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED, # Código para creación exitosa
    summary="Crear un Nuevo Post (Borrador)",
    description="Crea un nuevo post en estado de borrador (o el estado proporcionado) asociado al usuario autenticado.",
    tags=["Posts"]
)
async def create_post(
    post_data: PostCreate, # El cuerpo de la petición validado por Pydantic
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    user_id = current_user.user_id

    # Convertir el modelo Pydantic a un diccionario para la inserción
    # y añadir el user_id y los timestamps que no vienen del cliente (o que queremos controlar)
    new_post_dict = post_data.model_dump(exclude_unset=True) # exclude_unset para no enviar campos no seteados
    new_post_dict["user_id"] = str(user_id) # Asegurarse de que el UUID es string para Supabase
    
    # El status y scheduled_at pueden venir de PostCreate con sus defaults si no se proporcionan
    # created_at y updated_at deberían ser manejados por la DB (con default now())
    # o podrías establecerlos aquí si prefieres:
    # now_utc = datetime.now(pytz.utc)
    # new_post_dict["created_at"] = now_utc.isoformat()
    # new_post_dict["updated_at"] = now_utc.isoformat()

    try:
        # Insertar en la base de datos
        # Supabase-py v2.x style:
        query = supabase.table("posts").insert(new_post_dict).select().single().execute()
        # Supabase-py v1.x style (si insert devolvía los datos directamente):
        # query = supabase.table("posts").insert(new_post_dict).execute()


        if not query.data: # Si hubo un problema y no se devolvieron datos (aunque insert suele dar error antes)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear el post o no se obtuvieron los datos del post creado."
            )
        
        created_post_data = query.data
        
        # Validar la salida con PostResponse (esto también asegura que los campos
        # como id, created_at, updated_at generados por la DB estén presentes)
        return PostResponse.model_validate(created_post_data)

    except Exception as e:
        # Loguear el error `e`
        print(f"Error creando post para user {user_id}: {e}")
        # Revisar si es un error de Supabase por constraint violation (ej. UNIQUE)
        # o algún otro error de la base de datos.
        # Por ahora, un error genérico 500.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error al crear el post: {str(e)}"
        )

@router.get(
    "/{post_id}", # Asumiendo que el prefix "/posts" está en main.py
    response_model=PostResponse,
    summary="Obtener un Post Específico",
    description="Recupera los detalles de un post específico por su ID, siempre que pertenezca al usuario autenticado y no esté eliminado (a menos que se especifique lo contrario implícitamente).",
    tags=["Posts"]
)
async def get_post_by_id(
    post_id: UUID = Path(..., description="El ID del post a recuperar"),
    # Podrías añadir un query param para permitir ver posts borrados lógicamente si fuera necesario:
    # include_deleted: bool = Query(False, description="Incluir el post si está marcado como eliminado"),
    current_user: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    user_id = current_user.user_id

    try:
        query = supabase.table("posts").select("*").eq("id", str(post_id)).eq("user_id", str(user_id))
        
        # Por defecto, no mostramos posts borrados lógicamente al pedirlos por ID.
        # Si quisieras permitirlo, necesitarías el query param `include_deleted`
        # y una lógica similar a la de `get_posts`.
        # if not include_deleted:
        query = query.is_("deleted_at", None) # Solo traer si deleted_at ES NULL

        # .single() asegura que esperamos un solo resultado o ninguno.
        # Si no se encuentra, query.data será None.
        response = query.single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario, o ha sido eliminado."
            )
        
        post_data = response.data
        return PostResponse.model_validate(post_data)

    except HTTPException as http_exc:
        raise http_exc # Re-lanzar excepciones HTTP que ya hayamos manejado
    except Exception as e:
        print(f"Error obteniendo post {post_id} para user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al obtener el post."
        )

# ... (create_post, soft_delete_post) ...

# app/api/v1/routers/posts.py
# PATCH para actualizar parcialmente un post (o cambiar su estado)
@router.patch(
    "/{post_id}", 
    response_model=PostResponse,
    summary="Actualizar Parcialmente un Post / Cambiar Estado",
    description="...",
    tags=["Posts"]
)
async def update_post_partial(
    post_update_data: PostUpdate,                                        # Cuerpo de la petición (sin default)
    post_id: UUID = Path(..., description="El ID del post a actualizar"), # Parámetro de ruta (con default)
    current_user: TokenData = Depends(get_current_user),                 # Dependencia
    supabase: Client = Depends(get_supabase_client)                      # Dependencia
):
    user_id = current_user.user_id
    update_data_dict = post_update_data.model_dump(exclude_unset=True)

    if not update_data_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron datos para actualizar."
        )

    try:
        query = (
            supabase.table("posts")
            .update(update_data_dict)
            .eq("id", str(post_id))
            .eq("user_id", str(user_id))
            .is_("deleted_at", None)
            .select()
            .single()
            .execute()
        )

        if not query.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post con ID {post_id} no encontrado, no pertenece al usuario, o está eliminado y no puede ser modificado."
            )
        
        updated_post_data = query.data
        return PostResponse.model_validate(updated_post_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error actualizando parcialmente post {post_id} para user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al intentar actualizar el post."
        )
