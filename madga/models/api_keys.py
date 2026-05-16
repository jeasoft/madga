"""Per-user API keys.

Each user can mint multiple keys with labels (e.g. "iOS app", "CI bot",
"Zapier"). Keys are checked alongside the per-Site api_key on the headless
API: either authenticates a request, but per-user keys ALSO populate
request.user so view-level permissions work.

A user is bound to one or more Sites via SiteUser; an API key derives
the active site from the user's first SiteUser membership. If the user
belongs to multiple sites, the key's `site` FK pins which one.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models

from .base import TimestampMixin


def _new_key() -> str:
    # 32-byte secret as urlsafe base64 → ~43 chars, prefixed with `madga_` so
    # leaked tokens are scannable in logs.
    return "madga_" + secrets.token_urlsafe(32)


class UserApiKey(TimestampMixin, models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="madga_api_keys",
    )
    site = models.ForeignKey(
        "madga.Site",
        on_delete=models.CASCADE,
        related_name="user_api_keys",
        null=True,
        blank=True,
        help_text="Pin this key to a specific site. NULL = derive from user's first SiteUser.",
    )
    label = models.CharField(
        max_length=80,
        help_text="Human-readable name for this key (e.g. 'iOS app').",
    )
    key = models.CharField(max_length=64, unique=True, default=_new_key)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["key"])]

    def __str__(self) -> str:
        return f"{self.label} ({self.user})"

    def display_key(self) -> str:
        """Return a masked version safe for the UI: madga_…last8."""
        if len(self.key) <= 12:
            return self.key
        return f"{self.key[:8]}…{self.key[-6:]}"

    def rotate(self) -> str:
        self.key = _new_key()
        self.save(update_fields=["key", "updated_at"])
        return self.key
