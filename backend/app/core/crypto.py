"""Chiffrement symétrique (Fernet) des secrets stockés en base, ex. le mot de passe SMTP.

La clé dérive de SETTINGS_ENCRYPTION_KEY, à défaut de SECRET_KEY. Si cette clé change, les secrets
déjà enregistrés deviennent illisibles : il faut les ressaisir (le service le signale proprement).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    material = (settings.settings_encryption_key or settings.secret_key).encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
