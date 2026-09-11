from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class TokenEncryptionNotConfigured(RuntimeError):
    pass


@lru_cache
def _fernet() -> Fernet:
    key = settings.linkedin_token_encryption_key

    if key is None:
        raise TokenEncryptionNotConfigured(
            "LINKEDIN_TOKEN_ENCRYPTION_KEY is not set."
        )

    return Fernet(key.get_secret_value().encode())


def encrypt_token(raw_token: str) -> str:
    return _fernet().encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Stored token could not be decrypted — the encryption "
            "key may have changed."
        ) from exc
