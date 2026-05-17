"""SiteOAuthApp — per-Site override of MADGA_OAUTH global credentials.

Most SaaS tenants are happy using the operator's shared OAuth app
(``MADGA_OAUTH`` in settings.py). But enterprise tenants sometimes
want their OWN registered app per platform so:

- The OAuth consent screen says "Acme Corp" instead of "aplica.do"
- They control their own rate limits / quotas
- They keep separate audit logs in their own developer console

One row = one (Site, publisher_key) override. When present, the
Publisher's ``oauth_client_credentials(site=...)`` returns the
override's values; otherwise it falls back to settings. Tokens
(per-user access tokens) still live in PublisherAccount and are
unaffected.

Client secrets are encrypted at rest with the existing Fernet
helper (``madga.encryption``) — same key as PublisherAccount.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


class SiteOAuthApp(UUIDMixin, TimestampMixin, models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="oauth_apps",
    )
    publisher_key = models.CharField(
        max_length=50,
        help_text=_("Publisher this override applies to (e.g. 'twitter', 'instagram')."),
    )
    client_id = models.CharField(max_length=200)
    _client_secret_enc = models.TextField(
        blank=True, db_column="client_secret_enc",
        help_text=_("Fernet ciphertext of the secret."),
    )
    notes = models.CharField(
        max_length=300, blank=True,
        help_text=_("Internal note — shown on the Channels page (e.g. 'Acme corporate app')."),
    )

    class Meta:
        unique_together = [["site", "publisher_key"]]
        ordering = ["publisher_key"]
        verbose_name = _("Site OAuth app")
        verbose_name_plural = _("Site OAuth apps")

    def __str__(self) -> str:
        return f"{self.publisher_key} app @ {self.site}"

    def set_secret(self, plain: str) -> None:
        from madga.encryption import encrypt
        self._client_secret_enc = encrypt(plain or "")

    def get_secret(self) -> str:
        from madga.encryption import safe_decrypt
        return safe_decrypt(self._client_secret_enc, default="")
