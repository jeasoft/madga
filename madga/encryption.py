"""Symmetric encryption for storing sensitive credentials at rest.

Used by :class:`madga.models.PublisherAccount` to hold things like
LinkedIn access tokens, Twitter API secrets, etc., without leaving
them in plaintext in the database.

Key derivation:
  - prefers ``settings.MADGA_CREDENTIAL_KEY`` (a 32-byte url-safe
    base64-encoded key, generate with ``Fernet.generate_key()``)
  - falls back to a key derived from ``settings.SECRET_KEY`` for dev
    convenience (NOT recommended for production: if SECRET_KEY leaks,
    every stored credential decrypts; if you rotate SECRET_KEY, every
    stored credential becomes garbage).

Rotation pattern: set ``MADGA_CREDENTIAL_KEYS`` to a list — the first
entry encrypts new values, every entry can decrypt. Rotate by
prepending a new key, re-saving each PublisherAccount (the next save
re-encrypts under the new key), and eventually removing the old key.
"""

from __future__ import annotations

import base64
import hashlib

from django.conf import settings


def _derive_from_secret_key() -> bytes:
    """Derive a Fernet-shaped key from settings.SECRET_KEY."""
    raw = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(raw)


def _keys() -> list[bytes]:
    """Return all candidate Fernet keys, decrypt order (newest first)."""
    explicit = getattr(settings, "MADGA_CREDENTIAL_KEYS", None)
    if explicit:
        return [k.encode("utf-8") if isinstance(k, str) else k for k in explicit]
    single = getattr(settings, "MADGA_CREDENTIAL_KEY", None)
    if single:
        return [single.encode("utf-8") if isinstance(single, str) else single]
    return [_derive_from_secret_key()]


def encrypt(plain: str) -> str:
    """Encrypt a string. Returns a base64-ish urlsafe ciphertext token."""
    from cryptography.fernet import Fernet, MultiFernet

    keys = _keys()
    f = MultiFernet([Fernet(k) for k in keys])
    return f.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """Decrypt a ciphertext from :func:`encrypt`. Raises on failure."""
    from cryptography.fernet import Fernet, MultiFernet

    keys = _keys()
    f = MultiFernet([Fernet(k) for k in keys])
    return f.decrypt(token.encode("ascii")).decode("utf-8")


def safe_decrypt(token: str | None, default: str = "") -> str:
    """Decrypt or return ``default`` on any failure (corrupt, missing, etc.)."""
    if not token:
        return default
    try:
        return decrypt(token)
    except Exception:  # noqa: BLE001
        return default
