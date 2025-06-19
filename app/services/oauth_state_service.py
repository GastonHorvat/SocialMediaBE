# app/services/social/oauth_state_service.py
import logging
import json
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from app.db.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class OAuthStateService:
    TABLE_NAME = "oauth_states"

    def __init__(self, db_client: Any):
        """
        El constructor ahora requiere que se le pase el cliente de la base de datos.
        Esto se llama Inyección de Dependencias.
        """
        if db_client is None:
            logger.critical("FATAL: El cliente de base de datos (supabase_client) no está disponible. El servicio de estado OAuth no puede operar.")
            raise RuntimeError("El cliente de base de datos no está inicializado.")
        self.db = db_client

    def create_oauth_state(
        self,
        state: str,
        code_verifier: str,
        provider: str,
        user_id: UUID,
        organization_id: UUID
    ) -> None:
        """Crea un nuevo registro de estado OAuth en la base de datos."""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            payload = {
                "user_id": str(user_id),
                "organization_id": str(organization_id)
            }
            record = {
                "state": state,
                "provider": provider,
                "code_verifier": code_verifier,
                "payload": json.dumps(payload),
                "expires_at": expires_at.isoformat()
            }
            
            # Usamos self.db en lugar de supabase_client directamente
            self.db.table(self.TABLE_NAME).insert(record).execute()
            logger.info(f"Estado OAuth creado para el provider '{provider}' con state '{state[:8]}...'.")
        except Exception as e:
            logger.error(f"Fallo al crear el estado OAuth: {e}", exc_info=True)
            raise

    def consume_oauth_state(self, state: str, provider: str) -> Optional[Dict[str, Any]]:
        """Busca un estado, lo valida, lo borra y devuelve sus datos. Un solo uso."""
        try:
            response = self.db.table(self.TABLE_NAME)\
                .select("*")\
                .eq("state", state)\
                .eq("provider", provider)\
                .single()\
                .execute()

            record = response.data
            if not record:
                logger.warning(f"Intento de consumir estado OAuth no encontrado: '{state}'")
                return None
            
            expires_at = datetime.fromisoformat(record['expires_at'])
            if expires_at < datetime.now(timezone.utc):
                logger.warning(f"Intento de consumir estado OAuth expirado: '{state}'")
                self.db.table(self.TABLE_NAME).delete().eq("state", state).execute()
                return None

            self.db.table(self.TABLE_NAME).delete().eq("state", state).execute()
            logger.info(f"Estado OAuth consumido y eliminado exitosamente: '{state[:8]}...'.")
            
            return {
                "code_verifier": record["code_verifier"],
                "payload": json.loads(record["payload"])
            }
        except Exception as e:
            logger.error(f"Fallo al consumir el estado OAuth '{state}': {e}", exc_info=True)
            return None

# --- CORRECCIÓN CLAVE ---
# Creamos la instancia única del servicio pasándole el cliente de Supabase
# como el argumento 'db_client' que ahora requiere su __init__.
oauth_state_service = OAuthStateService(db_client=supabase_client)