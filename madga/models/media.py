"""Media library."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


class MediaFile(UUIDMixin, TimestampMixin, models.Model):
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_DOCUMENT = "document"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_IMAGE, _("Image")),
        (TYPE_VIDEO, _("Video")),
        (TYPE_DOCUMENT, _("Document")),
        (TYPE_OTHER, _("Other")),
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

    # Variants — populated by the post-save image optimizer. Each entry is
    # {"url": "...", "width": int, "height": int, "format": "webp|jpeg"}.
    # The biggest is always under the "xl" key; smaller ones under
    # "lg", "md", "sm". The optimizer is best-effort: a failure leaves
    # this empty and falls back to the original file at runtime.
    variants = models.JSONField(default=dict, blank=True)

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

    def srcset(self, fmt: str = "webp") -> str:
        """Return an HTML ``srcset`` value for this MediaFile.

        Skips variants whose format doesn't match. Falls back to the
        original file URL when no variants exist.
        """
        items = []
        for v in (self.variants or {}).values():
            if v.get("format") != fmt:
                continue
            url = v.get("url")
            w = v.get("width")
            if url and w:
                items.append(f"{url} {w}w")
        if not items and self.file:
            return self.file.url
        return ", ".join(items)
