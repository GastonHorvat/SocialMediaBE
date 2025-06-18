# app/services/social/linkedin_service.py

import logging
from uuid import UUID
import httpx
from typing import Optional

# Importamos el servicio de conexiones que ya tenemos
from app.services.social.connections_service import connections_service

logger = logging.getLogger(__name__)

class LinkedInService:
    API_BASE_URL = "https://api.linkedin.com/v2"

    async def publish_post(
        self,
        connection_id: UUID,
        post_content: str,
        media_url: Optional[str] = None
    ) -> dict:
        """
        Publica un post en LinkedIn. Maneja tanto posts de texto como de imagen.
        """
        logger.info(f"Iniciando publicación en LinkedIn para connection_id: {connection_id}")
        access_token = await connections_service.get_valid_access_token(connection_id)
        connection = await connections_service.get_connection_by_id(connection_id)
        
        if not connection or not connection.get("platform_user_id"):
            logger.error(f"No se pudo obtener el platform_user_id para la conexión {connection_id}")
            raise ValueError("ID de usuario de LinkedIn no encontrado en la conexión.")
        
        author_urn = f"urn:li:person:{connection['platform_user_id']}"
        
        # Es buena práctica especificar la versión de la API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202405" 
        }

        image_asset_id = None
        if media_url:
            logger.info(f"Iniciando flujo de subida de imagen para LinkedIn. URL: {media_url}")
            try:
                image_asset_id = await self._upload_image(author_urn, media_url, headers)
                logger.info(f"Imagen subida a LinkedIn exitosamente. Asset ID: {image_asset_id}")
            except Exception as e:
                logger.error(f"Fallo en el proceso de subida de imagen a LinkedIn: {e}", exc_info=True)
                raise Exception(f"No se pudo procesar la imagen para LinkedIn: {e}")

        # Construir el payload final del post
        payload = self._build_post_payload(author_urn, post_content, image_asset_id)
        
        # Realizar la petición final para crear el post
        async with httpx.AsyncClient() as client:
            logger.debug(f"Enviando payload a LinkedIn: {payload}")
            try:
                response = await client.post(f"{self.API_BASE_URL}/ugcPosts", json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Post publicado exitosamente en LinkedIn. ID de Post: {response.headers.get('x-restli-id')}")
                return response.json()
            except httpx.HTTPStatusError as e:
                error_details = e.response.json()
                logger.error(f"Error de la API de LinkedIn al publicar: {error_details}")
                raise Exception(f"Error al publicar en LinkedIn: {error_details.get('message', str(e))}")
            except httpx.RequestError as e:
                logger.error(f"Error de red al conectar con LinkedIn: {e}", exc_info=True)
                raise Exception("Error de red al conectar con LinkedIn.")

    async def _upload_image(self, author_urn: str, image_url: str, headers: dict) -> str:
        """Implementa el flujo de 3 pasos para subir una imagen a LinkedIn."""
        async with httpx.AsyncClient() as client:
            # PASO A: Registrar la subida
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author_urn,
                    "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                }
            }
            resp_register = await client.post(f"{self.API_BASE_URL}/assets?action=registerUpload", json=register_payload, headers=headers)
            resp_register.raise_for_status()
            upload_data = resp_register.json()
            
            upload_url = upload_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = upload_data["value"]["asset"]

            # PASO B: Descargar la imagen de la URL y subir los bytes a LinkedIn
            resp_image = await client.get(image_url)
            resp_image.raise_for_status()
            image_bytes = resp_image.content

            upload_headers = {"Authorization": headers["Authorization"], "Content-Type": "application/octet-stream"}
            resp_upload = await client.put(upload_url, content=image_bytes, headers=upload_headers)
            resp_upload.raise_for_status()

            # PASO C: Devolver el asset ID
            return asset_id

    def _build_post_payload(self, author_urn: str, post_content: str, image_asset_id: Optional[str]) -> dict:
        """Construye el cuerpo del post dependiendo de si hay una imagen o no."""
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_content},
                    "shareMediaCategory": "IMAGE" if image_asset_id else "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        if image_asset_id:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {"status": "READY", "media": image_asset_id}
            ]
        
        return payload

linkedin_service = LinkedInService()