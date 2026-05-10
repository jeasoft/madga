"""Site model — global config for an installation."""

import secrets

from django.db import models

from .base import TimestampMixin


def _new_api_key() -> str:
    return secrets.token_urlsafe(48)[:64]


class Site(TimestampMixin, models.Model):
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="madga/site/", blank=True, null=True)
    favicon = models.ImageField(upload_to="madga/site/", blank=True, null=True)

    # Theme tokens (v0.2 surfaces these in Studio → Theme)
    accent_color = models.CharField(max_length=7, default="#6C63FF")
    heading_font = models.CharField(max_length=50, default="Geist")
    body_font = models.CharField(max_length=50, default="Geist")
    border_radius = models.PositiveIntegerField(default=8)
    content_density = models.CharField(
        max_length=20,
        default="comfortable",
        choices=[
            ("comfortable", "Comfortable"),
            ("compact", "Compact"),
            ("spacious", "Spacious"),
        ],
    )
    color_scheme = models.CharField(
        max_length=10,
        default="auto",
        choices=[("auto", "Auto"), ("light", "Light"), ("dark", "Dark")],
    )
    theme = models.CharField(max_length=50, default="essay")

    # SEO defaults
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(blank=True)

    timezone = models.CharField(max_length=50, default="America/Santo_Domingo")
    is_active = models.BooleanField(default=True)

    # Per-site layout/nav settings stored as JSON for flexibility
    settings = models.JSONField(default=dict, blank=True)

    # Analytics & tracking — injected into the public site head when set.
    google_analytics_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="GA4 measurement id, e.g. G-XXXXXXX. Empty disables tracking.",
    )
    facebook_pixel_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="Meta (Facebook) Pixel numeric id. Empty disables.",
    )

    api_key = models.CharField(max_length=64, unique=True, default=_new_api_key)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def rotate_api_key(self) -> str:
        self.api_key = _new_api_key()
        self.save(update_fields=["api_key"])
        return self.api_key
