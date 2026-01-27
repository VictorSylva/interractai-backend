import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# Use SECRET_KEY for generating the encryption key if not provided explicitly
# Fernet needs 32 url-safe base64-encoded bytes
RAW_KEY = os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY", "fallback-secret-key-at-least-32-chars-long")

# Standardize to 32 bytes and base64 encode
import base64
import hashlib
key_bytes = hashlib.sha256(RAW_KEY.encode()).digest()
FERNET_KEY = base64.urlsafe_b64encode(key_bytes)
cipher_suite = Fernet(FERNET_KEY)

def encrypt_token(token: str) -> str:
    """Encrypts a string token using Fernet."""
    if not token:
        return None
    try:
        return cipher_suite.encrypt(token.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a Fernet encrypted string."""
    if not encrypted_token:
        return None
    try:
        return cipher_suite.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None
