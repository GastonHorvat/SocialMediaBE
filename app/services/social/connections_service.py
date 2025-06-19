# app/services/social/connections_service.py
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import List, Dict, Any, Optional

from app.db.supabase_client import supabase_client
from app.services.security_service import security_service  # <-- Importamos el nuevo servicio
from app.models.connection_models import ConnectionStatusEnum

logger = logging.getLogger(__name__)

class ConnectionsService:
    TABLE_NAME = "social_connections"

    def create_or_update_connection(
        self,
        organization_id: UUID,
        user_id: UUID,
        platform: str,
        platform_user_id: str,
        platform_account_name: str,
        token_data: dict,
    ) -> Dict[str, Any]:
        """
        Crea o actualiza una conexión social en la base de datos.
        El token de acceso se almacena siempre encriptado.
        No se almacena el refresh token, ya que LinkedIn no lo proporciona de forma fiable.
        """
        try:
            access_token = token_data['access_token']
            
            # Encriptar el token de acceso antes de guardarlo
            encrypted_token = security_service.encrypt_data(access_token)
            
            # Calcular la fecha de expiración a partir de 'expires_in'
            expires_in_seconds = token_data.get('expires_in', 3600) # Default a 1 hora si no viene
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

            connection_payload = {
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "platform": platform.lower(),
                "platform_user_id": platform_user_id,
                "platform_account_name": platform_account_name,
                "encrypted_access_token": encrypted_token,
                "access_token_expires_at": expires_at.isoformat(),
                "scopes": token_data.get('scope', ''),
                "status": ConnectionStatusEnum.ACTIVE.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Usar upsert para crear o actualizar la conexión si ya existe.
            # El conflicto se basa en la combinación única de organización y plataforma.
            response = supabase_client.table(self.TABLE_NAME)\
                .upsert(connection_payload, on_conflict="organization_id,platform")\
                .execute()
            
            logger.info(f"Conexión de '{platform}' creada/actualizada para la organización {organization_id}.")
            return response.data[0]

        except Exception as e:
            logger.error(f"Fallo al guardar la conexión de '{platform}': {e}", exc_info=True)
            raise

    def get_valid_access_token(self, connection_id: UUID) -> str:
        """
        Obtiene un token de acceso desencriptado si la conexión es válida y no ha expirado.
        Lanza un error si la conexión no es válida o el token ha expirado.
        """
        connection = self.get_connection_by_id(connection_id)
        if not connection:
            raise ValueError(f"Conexión con ID {connection_id} no encontrada.")

        expires_at = datetime.fromisoformat(connection['access_token_expires_at'])
        if expires_at <= datetime.now(timezone.utc):
            # El token ha expirado. Actualizamos el estado en la DB.
            self.update_connection_status(connection_id, ConnectionStatusEnum.EXPIRED)
            logger.warning(f"El token de acceso para la conexión {connection_id} ha expirado.")
            raise ValueError("El token de acceso ha expirado. Se requiere re-autenticación.")

        encrypted_token = connection.get("encrypted_access_token")
        if not encrypted_token:
            raise ValueError("La conexión no tiene un token de acceso válido almacenado.")
            
        return security_service.decrypt_data(encrypted_token)

    def get_connection_by_id(self, connection_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca una conexión por su ID."""
        try:
            response = supabase_client.table(self.TABLE_NAME).select("*").eq("id", str(connection_id)).single().execute()
            return response.data
        except Exception:
            return None

    def get_connections_by_org(self, organization_id: UUID) -> List[Dict[str, Any]]:
        """Recupera todas las conexiones para una organización."""
        try:
            response = supabase_client.table(self.TABLE_NAME)\
                .select("*")\
                .eq("organization_id", str(organization_id))\
                .order("created_at", desc=True)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al recuperar conexiones para la organización {organization_id}: {e}", exc_info=True)
            return []

    def delete_connection(self, connection_id: UUID) -> bool:
        """Elimina una conexión de la base de datos."""
        try:
            supabase_client.table(self.TABLE_NAME).delete().eq("id", str(connection_id)).execute()
            logger.info(f"Conexión {connection_id} eliminada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar la conexión {connection_id}: {e}", exc_info=True)
            return False

    def update_connection_status(self, connection_id: UUID, status: ConnectionStatusEnum):
        """Actualiza el estado de una conexión (ej. a EXPIRED)."""
        try:
            supabase_client.table(self.TABLE_NAME)\
                .update({"status": status.value})\
                .eq("id", str(connection_id))\
                .execute()
            logger.info(f"Estado de la conexión {connection_id} actualizado a '{status.value}'.")
        except Exception as e:
            logger.error(f"No se pudo actualizar el estado de la conexión {connection_id}: {e}", exc_info=True)


# Instancia única del servicio
connections_service = ConnectionsService()