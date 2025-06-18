# app/services/social/connections_service.py
# VERSIÓN FINAL Y COMPLETA - REVISADA POR ELI

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from cryptography.fernet import Fernet
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.db.supabase_client import supabase_client
from app.core.oauth_clients import oauth
from app.models.connection_models import ConnectionStatusEnum

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)

class ConnectionsService:
    def __init__(self):
        if not settings.TOKENS_ENCRYPTION_KEY:
            logger.critical("FATAL: TOKENS_ENCRYPTION_KEY no está configurada. La aplicación no puede iniciarse de forma segura.")
            raise ValueError("TOKENS_ENCRYPTION_KEY no está configurada.")
        self.fernet = Fernet(settings.TOKENS_ENCRYPTION_KEY.encode())

    # --- Métodos de Encriptación ---
    def _encrypt_token(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        return self.fernet.decrypt(encrypted_token.encode()).decode()

    # --- Métodos de Gestión de Conexiones ---

    def create_or_update_linkedin_connection(self, organization_id: UUID, connected_by_user_id: UUID, linkedin_user_id: str, profile_data: dict, token_data: dict):
        if not linkedin_user_id: raise ValueError("El 'sub' (ID de usuario) no fue proporcionado.")
        
        encrypted_access_token = self.encrypt_token(token_data['access_token'])
        encrypted_refresh_token = self.encrypt_token(token_data.get('refresh_token')) if token_data.get('refresh_token') else None
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600))
        
        connection_data = {
            "organization_id": str(organization_id),
            "connected_by_user_id": str(connected_by_user_id),
            "platform": "linkedin", "platform_user_id": linkedin_user_id,
            "platform_account_name": profile_data.get('name'),
            "platform_account_avatar_url": profile_data.get('picture'),
            "access_token": encrypted_access_token,
            "refresh_token": encrypted_refresh_token,
            "expires_at": expires_at.isoformat(),
            "scopes": token_data.get('scope', '').split(' '),
            "status": "ACTIVE",
            "metadata": profile_data
        }
        
        try:
            supabase_client.table("social_connections").upsert(connection_data).execute()
        except Exception as e:
            print(f"ERROR: Fallo en el upsert de la conexión de LinkedIn: {e}")
            raise

    async def get_connection_by_id(self, connection_id: UUID) -> Optional[Dict[str, Any]]:
        try:
            response = supabase_client.table("social_connections").select("*").eq("id", str(connection_id)).single().execute()
            return response.data
        except Exception:
            logger.warning(f"No se encontró ninguna conexión con ID: {connection_id}")
            return None

    async def get_valid_access_token(self, connection_id: UUID) -> str:
        connection = self.get_connection_by_id(connection_id)
        if not connection:
            raise ValueError(f"Conexión con ID {connection_id} no encontrada.")

        if self._is_token_expiring(connection.get("expires_at")):
            logger.info(f"Token para conexión {connection_id} está por expirar. Iniciando refresco.")
            connection = await self._refresh_linkedin_token(connection)

        encrypted_token = connection.get("access_token")
        if not encrypted_token:
            raise ValueError("La conexión no tiene un token de acceso válido.")
            
        return self._decrypt_token(encrypted_token)

    def _is_token_expiring(self, expires_at_str: Optional[str]) -> bool:
        if not expires_at_str:
            return True
        expires_at = datetime.fromisoformat(expires_at_str)
        # Refrescar si expira en los próximos 5 minutos.
        return expires_at < (datetime.now(timezone.utc) + timedelta(minutes=5))

    async def _refresh_linkedin_token(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        connection_id = UUID(connection['id'])
        encrypted_refresh_token = connection.get("refresh_token")
        
        if not encrypted_refresh_token:
            self._update_connection_status(connection_id, ConnectionStatusEnum.REQUIRES_REAUTH)
            logger.warning(f"Se requiere re-autenticación para la conexión {connection_id}. No hay refresh_token.")
            raise ValueError("No hay refresh_token disponible. Se requiere re-autenticación manual.")
        
        refresh_token = self._decrypt_token(encrypted_refresh_token)

        try:
            new_token_data = await oauth.linkedin.fetch_access_token(refresh_token=refresh_token, grant_type='refresh_token')
            update_payload = {
                "access_token": self._encrypt_token(new_token_data['access_token']),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=new_token_data['expires_in'])).isoformat(),
                "scopes": new_token_data.get('scope', '').split(' '),
                "status": ConnectionStatusEnum.ACTIVE.value
            }
            if 'refresh_token' in new_token_data:
                update_payload["refresh_token"] = self._encrypt_token(new_token_data['refresh_token'])

            response = supabase_client.table("social_connections").update(update_payload).eq("id", str(connection_id)).execute()
            logger.info(f"Token para conexión {connection_id} refrescado y actualizado en DB.")
            return response.data[0]
        except Exception as e:
            logger.error(f"Fallo al refrescar token para conexión {connection_id}. Error: {e}", exc_info=True)
            self._update_connection_status(connection_id, ConnectionStatusEnum.REQUIRES_REAUTH)
            raise Exception("No se pudo refrescar el token. La autorización puede haber sido revocada.")

    async def _update_connection_status(self, connection_id: UUID, status: ConnectionStatusEnum):
        try:
            supabase_client.table("social_connections").update({"status": status.value}).eq("id", str(connection_id)).execute()
            logger.info(f"Estado de la conexión {connection_id} actualizado a {status.value}.")
        except Exception as e:
            logger.error(f"No se pudo actualizar el estado de la conexión {connection_id}: {e}", exc_info=True)

    async def get_connections_by_org(self, organization_id: UUID) -> List[Dict[str, Any]]:
        try:
            response = supabase_client.table("social_connections").select("*").eq("organization_id", str(organization_id)).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al recuperar conexiones para la organización {organization_id}: {e}", exc_info=True)
            return []

    async def delete_connection(self, connection_id: UUID) -> bool:
        try:
            supabase_client.table("social_connections").delete().eq("id", str(connection_id)).execute()
            logger.info(f"Conexión {connection_id} eliminada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar la conexión {connection_id}: {e}", exc_info=True)
            return False

connections_service = ConnectionsService()