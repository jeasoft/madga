"""Form blocks: FormSubmission model.

A site embeds a ContactFormBlock somewhere on its public pages
(homepage builder or inside a Post body). When a visitor fills it
and POSTs, MADGA creates a ``FormSubmission`` row with the JSON
data, optionally emails the configured recipient, and fires a
``form.submitted`` webhook event.

Studio inbox at /studio/inbox/ shows submissions per Site with
search + mark-read + export.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


class FormSubmission(UUIDMixin, TimestampMixin, models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="form_submissions"
    )
    # Block UUID that produced this submission. We store the raw UUID
    # (not an FK) because the block might be deleted later but we want
    # to keep the historical submissions.
    block_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    form_key = models.CharField(
        max_length=80, blank=True,
        help_text=_("Short identifier the host project picks ('contact', 'apply', …)"),
    )
    source_url = models.URLField(max_length=500, blank=True)
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Form submission")
        verbose_name_plural = _("Form submissions")

    def __str__(self) -> str:
        sender = (self.data.get("email") if isinstance(self.data, dict) else "") or "(anonymous)"
        return f"{self.form_key or 'form'}: {sender}"
