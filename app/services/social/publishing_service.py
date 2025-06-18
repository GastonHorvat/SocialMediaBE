# app/services/social/publishing_service.py
# VERSIÓN FINAL - LÓGICA SÍNCRONA/ASÍNCRONA MIXTA CORRECTA

from uuid import UUID

from app.services.social.linkedin_service import linkedin_service
from app.services.social.connections_service import connections_service
from app.db.supabase_client import supabase_client

class PublishingService:
    def __init__(self):
        self.platform_services = {"linkedin": linkedin_service}

    # Este método debe ser async porque llama a linkedin_service.publish_post que es async
    async def publish_post(self, post_id: UUID, connection_id: UUID) -> dict:
        # La llamada a get_connection_by_id ahora es síncrona
        connection = connections_service.get_connection_by_id(connection_id)
        if not connection: raise ValueError(f"Conexión con ID {connection_id} no encontrada.")
        
        platform = connection.get("platform")
        if not platform: raise ValueError("La conexión no tiene una plataforma especificada.")
        
        service_specialist = self.platform_services.get(platform)
        if not service_specialist: raise NotImplementedError(f"La publicación para la plataforma '{platform}' no está implementada.")
            
        try:
            # La llamada a la DB es síncrona
            post_response = supabase_client.table("posts").select("content, media_url").eq("id", str(post_id)).single().execute()
            post_data = post_response.data
            if not post_data: raise ValueError(f"Post con ID {post_id} no encontrado.")
            post_content, media_url = post_data.get("content"), post_data.get("media_url")
            if not post_content: raise ValueError(f"No se encontró contenido para el post.")
        except Exception:
            raise ValueError(f"Post con ID {post_id} no encontrado.")

        # La llamada al especialista SÍ es async
        result = await service_specialist.publish_post(
            connection_id=connection_id,
            post_content=post_content,
            media_url=media_url
        )
        
        return {
            "message": f"Post enviado para publicación en {platform.capitalize()}.",
            "platform": platform,
            "publication_details": result
        }

publishing_service = PublishingService()