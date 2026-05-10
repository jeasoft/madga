"""Media library."""

from django.conf import settings
from django.db import models

from .base import TimestampMixin, UUIDMixin


class MediaFile(UUIDMixin, TimestampMixin, models.Model):
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_DOCUMENT = "document"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_IMAGE, "Imagen"),
        (TYPE_VIDEO, "Video"),
        (TYPE_DOCUMENT, "Documento"),
        (TYPE_OTHER, "Otro"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="media"
    )
    file = models.FileField(upload_to="madga/media/%Y/%m/")
    file_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_IMAGE
    )
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    alt_text = models.CharField(max_length=500, blank=True)
    caption = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="madga_uploads",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.filename or str(self.id)
