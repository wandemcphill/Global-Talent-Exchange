"""Field-level encryption for sensitive KYC/bank identifiers at rest.

Keys come from ``GTE_FIELD_ENCRYPTION_KEY`` (comma-separated Fernet keys; the
first encrypts, all decrypt via ``MultiFernet`` so rotation is supported).
Production-like environments require the variable at startup; development and
test derive a deterministic key from the auth secret so no env setup is needed.
"""

from __future__ import annotations

import base64
from functools import lru_cache
import hmac
from hashlib import sha256
import logging
import re

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

ENCRYPTION_PREFIX = "enc:v1:"
FIELD_ENCRYPTION_INFO = b"gtex-field-encryption-v1"
FIELD_INDEX_INFO = b"gtex-field-index-v1"
_PRODUCTION_ENVS = {"production", "prod", "staging", "release"}
_WHITESPACE_RE = re.compile(r"\s+")


def derive_key_from_secret(secret: str, *, info: bytes) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"gtex-field-encryption",
        info=info,
    )
    return hkdf.derive(secret.encode("utf-8"))


def derived_development_fernet_key(auth_secret: str) -> str:
    """Deterministic Fernet key for non-production environments."""
    return base64.urlsafe_b64encode(derive_key_from_secret(auth_secret, info=FIELD_ENCRYPTION_INFO)).decode("ascii")


def is_production_environment(app_env: str | None) -> bool:
    return (app_env or "").strip().lower() in _PRODUCTION_ENVS


def validate_field_encryption_keys(raw_value: str) -> None:
    """Raise a clear ValueError unless every key parses as a Fernet key."""
    keys = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not keys:
        raise ValueError(
            "GTE_FIELD_ENCRYPTION_KEY must contain at least one Fernet key. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    for index, key in enumerate(keys):
        try:
            Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"GTE_FIELD_ENCRYPTION_KEY entry #{index + 1} is not a valid Fernet key. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            ) from exc


def _settings():
    from app.core.config import get_settings

    return get_settings()


@lru_cache(maxsize=8)
def _multi_fernet(raw_keys: str) -> MultiFernet:
    keys = [part.strip() for part in raw_keys.split(",") if part.strip()]
    if not keys:
        raise ValueError("GTE_FIELD_ENCRYPTION_KEY is not configured.")
    return MultiFernet([Fernet(key.encode("utf-8")) for key in keys])


def _fernet() -> MultiFernet:
    raw = _settings().field_encryption_key or ""
    return _multi_fernet(raw)


@lru_cache(maxsize=4)
def _index_key(auth_secret: str) -> bytes:
    return derive_key_from_secret(auth_secret, info=FIELD_INDEX_INFO)


def encrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(ENCRYPTION_PREFIX):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTION_PREFIX}{token}"


def decrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(ENCRYPTION_PREFIX):
        # Legacy plaintext rows predate encryption-at-rest; read through.
        return value
    token = value[len(ENCRYPTION_PREFIX) :]
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def blind_index(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _WHITESPACE_RE.sub("", value)
    if not normalized:
        return None
    key = _index_key(_settings().auth_secret or "")
    return hmac.new(key, normalized.encode("utf-8"), sha256).hexdigest()


def identifier_hash_clause(column, term: str | None):
    """Exact-match predicate for a blind-index column.

    Blank terms (and terms that normalize to empty) return None. Callers must
    omit that result from the query: ``column == None`` compiles to ``IS NULL``
    and would match every row whose hash has not been populated.
    """
    hashed = blind_index(term)
    if hashed is None:
        return None
    return column == hashed


class EncryptedString(TypeDecorator):
    """String column that transparently encrypts values at rest."""

    impl = String
    cache_ok = True

    def __init__(self, length: int = 512, *args, **kwargs) -> None:
        super().__init__(length=length, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        return encrypt_field(value)

    def process_result_value(self, value, dialect):
        return decrypt_field(value)
