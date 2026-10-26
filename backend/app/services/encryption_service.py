import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


class EncryptionError(Exception):
    """Raised when encryption or decryption operations fail."""
    pass


class TokenEncryptionService:
    """
    Cryptographic service for securely storing OAuth refresh and access tokens at rest.
    Uses Fernet symmetric encryption with key derivation from configured secrets.
    """

    @staticmethod
    def _get_fernet() -> Fernet:
        raw_key = settings.GMAIL_TOKEN_ENCRYPTION_KEY or "outreachiq_default_dev_encryption_key_2026_xyz"
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        return Fernet(derived_key)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return ""
        try:
            fernet = cls._get_fernet()
            return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            raise EncryptionError("Failed to encrypt sensitive credential.") from exc

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            fernet = cls._get_fernet()
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            raise EncryptionError("Failed to decrypt stored credential.") from exc
