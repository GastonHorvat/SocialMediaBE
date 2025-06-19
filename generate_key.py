# generate_key.py
from cryptography.fernet import Fernet

# Genera una clave nueva, válida y segura en formato URL-safe base64
key = Fernet.generate_key()

print("--- TU NUEVA CLAVE DE ENCRIPTACIÓN ---")
print("Copia esta línea completa y pégala en tu archivo .env")
print(f"TOKENS_ENCRYPTION_KEY={key.decode()}")
print("---------------------------------------")