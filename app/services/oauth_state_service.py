# app/services/social/oauth_state_service.py
# SERVICIO PARA GESTIONAR EL ESTADO TEMPORAL DE OAUTH

import logging
import json
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from app.db.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class OAuthStateService:
    TABLE_NAME = "oauth_states"

    def create_oauth_state(
        self,
        state: str,
        code_verifier: str,
        provider: str,
        user_id: UUID,
        organization_id: UUID
    ) -> None:
        """
        Crea un nuevo registro de estado OAuth en la base de datos.
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            # Guardamos la info del usuario en el payload para recuperarla después
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
            
            supabase_client.table(self.TABLE_NAME).insert(record).execute()
            logger.info(f"Estado OAuth creado para el provider '{provider}' con state '{state[:8]}...'.")
        except Exception as e:
            logger.error(f"Fallo al crear el estado OAuth: {e}", exc_info=True)
            raise

    def consume_oauth_state(self, state: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Busca un estado, lo valida, lo borra y devuelve sus datos. Un solo uso.
        """
        try:
            # 1. Buscar el estado
            response = supabase_client.table(self.TABLE_NAME)\
                .select("*")\
                .eq("state", state)\
                .eq("provider", provider)\
                .single()\
                .execute()

            record = response.data
            if not record:
                logger.warning(f"Intento de consumir estado OAuth no encontrado: '{state}'")
                return None
            
            # 2. Validar que no haya expirado
            expires_at = datetime.fromisoformat(record['expires_at'])
            if expires_at < datetime.now(timezone.utc):
                logger.warning(f"Intento de consumir estado OAuth expirado: '{state}'")
                # Limpiamos el estado expirado
                supabase_client.table(self.TABLE_NAME).delete().eq("state", state).execute()
                return None

            # 3. Borrar el estado para que no se pueda reutilizar
            supabase_client.table(self.TABLE_NAME).delete().eq("state", state).execute()
            
            logger.info(f"Estado OAuth consumido y eliminado exitosamente: '{state[:8]}...'.")
            
            # Devolvemos el code_verifier y el payload
            return {
                "code_verifier": record["code_verifier"],
                "payload": json.loads(record["payload"])
            }
        except Exception as e:
            logger.error(f"Fallo al consumir el estado OAuth '{state}': {e}", exc_info=True)
            return None

# Creamos una instancia única del servicio para ser usada en la aplicación
oauth_state_service = OAuthStateService()