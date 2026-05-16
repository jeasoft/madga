"""PublisherAccount: per-Site connected channel.

One row per (Site, publisher_key, handle) tuple. Stores the encrypted
credentials each publisher needs to call its remote API (LinkedIn
access token, Twitter API key+secret, Mastodon access token, etc.)
plus display metadata so the studio Channels page can show "connected
as @aitorruiz" without exposing the secret.

Credentials live in ``_credentials_enc`` — a Fernet ciphertext of the
JSON-encoded dict. Use :meth:`get_credentials` / :meth:`set_credentials`
to round-trip them; never read or write ``_credentials_enc`` directly.
"""

from __future__ import annotations

import json

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


class PublisherAccount(UUIDMixin, TimestampMixin, models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="channels",
    )
    publisher_key = models.CharField(
        max_length=50,
        help_text=_("Key of a registered Publisher (e.g. 'twitter', 'linkedin')."),
    )
    handle = models.CharField(
        max_length=200, blank=True,
        help_text=_("Public handle/username shown in the studio (e.g. '@aitorruiz')."),
    )
    display_name = models.CharField(max_length=200, blank=True)
    audience_size = models.PositiveIntegerField(
        default=0,
        help_text=_("Cached follower/subscriber count for display."),
    )

    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    # Fernet ciphertext of a JSON dict. Never read/write directly — use
    # get_credentials / set_credentials.
    _credentials_enc = models.TextField(blank=True, db_column="credentials_enc")

    class Meta:
        unique_together = [["site", "publisher_key", "handle"]]
        ordering = ["publisher_key", "handle"]
        verbose_name = _("Channel")
        verbose_name_plural = _("Channels")

    def __str__(self) -> str:
        return f"{self.publisher_key}: {self.handle or '(unset)'} @ {self.site}"

    # ---- credentials round-trip ----------------------------------------

    def set_credentials(self, plain: dict) -> None:
        """Encrypt and store ``plain`` as the credentials blob."""
        from madga.encryption import encrypt
        self._credentials_enc = encrypt(json.dumps(plain or {}))

    def get_credentials(self) -> dict:
        """Decrypt the credentials. Returns ``{}`` on failure or empty."""
        from madga.encryption import safe_decrypt
        raw = safe_decrypt(self._credentials_enc, default="")
        if not raw:
            return {}
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    def pause(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def resume(self):
        self.is_active = True
        self.last_error = ""
        self.save(update_fields=["is_active", "last_error"])

    def record_use(self):
        from django.utils import timezone
        self.last_used_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["last_used_at", "last_error"])

    def record_error(self, msg: str):
        self.last_error = (msg or "")[:2000]
        self.save(update_fields=["last_error"])
