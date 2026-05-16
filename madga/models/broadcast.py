"""Broadcast: Subscriber + BroadcastJob.

The model layer for outbound publisher fan-out: when an editor publishes
a post, MADGA can broadcast it to multiple destinations — email
subscribers (built-in), LinkedIn, Twitter, Facebook, custom webhooks
(host projects register their own via `@register_publisher`).

A ``BroadcastJob`` is one (publisher × content) tuple with frozen
snapshot fields (subject, body) so editing the source post after the
fact doesn't rewrite history. ``Subscriber`` is the audience for the
built-in email publisher.
"""

import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


def _new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


class Subscriber(UUIDMixin, TimestampMixin, models.Model):
    """Per-site email subscriber for the built-in email publisher.

    A Subscriber may be linked to a User (created during signup if the
    user opted in) or stand alone (anonymous public signup, CSV import,
    or form-block submission). The unsubscribe token is a stable
    one-way string used in ``List-Unsubscribe`` headers.
    """

    SOURCE_SIGNUP = "signup"
    SOURCE_MANUAL = "manual"
    SOURCE_IMPORTED = "imported"
    SOURCE_FORM = "form"
    SOURCE_CHOICES = [
        (SOURCE_SIGNUP, _("Signup")),
        (SOURCE_MANUAL, _("Manual")),
        (SOURCE_IMPORTED, _("Imported")),
        (SOURCE_FORM, _("Form")),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="subscribers"
    )
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="madga_subscriptions",
    )
    locale = models.CharField(max_length=10, default="en")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    is_active = models.BooleanField(default=True, db_index=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("Set when the user confirms double opt-in. Empty means single opt-in."),
    )
    unsubscribe_token = models.CharField(
        max_length=64, unique=True, default=_new_unsubscribe_token
    )

    class Meta:
        unique_together = [["site", "email"]]
        ordering = ["-created_at"]
        verbose_name = _("Subscriber")
        verbose_name_plural = _("Subscribers")

    def __str__(self) -> str:
        return f"{self.email} @ {self.site}"

    def unsubscribe(self):
        from django.utils import timezone
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_active", "unsubscribed_at"])


class BroadcastJob(UUIDMixin, TimestampMixin, models.Model):
    """A single (publisher × content) broadcast.

    Created when an editor hits "Broadcast" in the studio. Snapshot
    fields are frozen at creation time so editing the source Post after
    the broadcast doesn't change what was sent.
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SENT = "sent"
    STATUS_PARTIAL = "partial"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_RUNNING, _("Running")),
        (STATUS_SENT, _("Sent")),
        (STATUS_PARTIAL, _("Partial")),
        (STATUS_FAILED, _("Failed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="broadcasts"
    )
    publisher_key = models.CharField(
        max_length=50,
        help_text=_("Key of a registered Publisher (e.g. email_subscribers, linkedin)."),
    )

    # Frozen content snapshot.
    subject = models.CharField(max_length=300)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    related_url = models.URLField(blank=True)

    # Optional traceability back to source content.
    related_post = models.ForeignKey(
        "madga.Post", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="broadcasts",
    )
    related_page = models.ForeignKey(
        "madga.Page", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="broadcasts",
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    scheduled_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("If set in the future, the worker won't pick the job up before this time."),
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    targets_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="madga_broadcasts_created",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Broadcast")
        verbose_name_plural = _("Broadcasts")
        indexes = [
            models.Index(fields=["site", "status"]),
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.publisher_key}: {self.subject[:40]} ({self.status})"

    @property
    def progress_pct(self) -> int:
        """For UI progress bars."""
        if not self.targets_count:
            return 0
        return int(100 * (self.sent_count + self.failed_count) / self.targets_count)

    def mark_running(self):
        from django.utils import timezone
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_finished(self):
        from django.utils import timezone
        if self.failed_count == 0:
            self.status = self.STATUS_SENT
        elif self.sent_count == 0:
            self.status = self.STATUS_FAILED
        else:
            self.status = self.STATUS_PARTIAL
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def cancel(self):
        from django.utils import timezone
        self.status = self.STATUS_CANCELLED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])
