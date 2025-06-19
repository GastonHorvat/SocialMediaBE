# app/services/security_service.py
import logging
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self, key: str):
        if not key:
            # Este es un error fatal para la aplicación.
            logger.critical("FATAL: TOKENS_ENCRYPTION_KEY no está configurada. El servicio de seguridad no puede operar y la aplicación no es segura.")
            raise ValueError("La clave de encriptación (TOKENS_ENCRYPTION_KEY) no puede estar vacía.")
        
        try:
            self.fernet = Fernet(key.encode('utf-8'))
        except Exception as e:
            logger.critical(f"FATAL: La TOKENS_ENCRYPTION_KEY proporcionada es inválida y no se puede usar para inicializar Fernet. Error: {e}")
            raise ValueError("La clave de encriptación proporcionada es inválida.")

    def encrypt_data(self, plain_text_data: str) -> str:
        # ... (sin cambios)
        try:
            return self.fernet.encrypt(plain_text_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Fallo al encriptar los datos: {e}", exc_info=True)
            raise ValueError("Error durante la encriptación.")

    def decrypt_data(self, encrypted_data: str) -> str:
        # ... (sin cambios)
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            logger.error("Token de desencriptación inválido. El token puede haber sido manipulado o la clave de encriptación cambió.")
            raise ValueError("Token de desencriptación inválido.")
        except Exception as e:
            logger.error(f"Fallo al desencriptar los datos: {e}", exc_info=True)
            raise ValueError("Error durante la desencriptación.")

security_service = SecurityService(key=settings.TOKENS_ENCRYPTION_KEY)