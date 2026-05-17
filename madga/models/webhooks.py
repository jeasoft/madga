"""Outbound webhooks: WebhookEndpoint + WebhookDelivery.

Host projects (aplica.do, miscore, etc.) subscribe to MADGA events
by creating a ``WebhookEndpoint`` row pointing at their own URL.
Whenever a tracked event fires inside MADGA (post.published,
subscriber.created, broadcast.sent, …) we POST a signed JSON
payload to every active endpoint that subscribed to that event.

The HMAC signature uses the endpoint's stored secret (each endpoint
generates its own — never reuses one across tenants) so receivers
can verify the call came from MADGA and wasn't replayed.

Delivery is fire-and-forget from the user's POV. A
``WebhookDelivery`` row is created for every attempt with the
request payload, response code/body snippet, and retry count.
Failed deliveries are retried with exponential backoff by the
``madga webhook-worker`` management subcommand.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimestampMixin, UUIDMixin


# Catalog of every event MADGA fires. Kept here (not in a free-form
# string field) so the studio UI can render checkboxes and the
# receiver knows what to expect. Host projects can add their own
# events at runtime by appending to ``REGISTERED_EVENTS``.
REGISTERED_EVENTS: list[tuple[str, str]] = [
    ("post.published", _("A post was published (status went draft→published)")),
    ("post.unpublished", _("A published post was reverted to draft or archived")),
    ("post.updated", _("A post was edited (any field)")),
    ("post.deleted", _("A post was moved to trash")),
    ("page.published", _("A page was published")),
    ("page.updated", _("A page was edited")),
    ("page.deleted", _("A page was deleted")),
    ("subscriber.created", _("A new email subscriber was added")),
    ("subscriber.unsubscribed", _("A subscriber opted out via the one-click link")),
    ("broadcast.sent", _("A broadcast finished sending")),
    ("broadcast.failed", _("A broadcast failed for every target")),
    ("media.uploaded", _("A media file was uploaded")),
]


def _new_webhook_secret() -> str:
    """Random URL-safe secret used to HMAC-sign every payload."""
    return secrets.token_urlsafe(32)


class WebhookEndpoint(UUIDMixin, TimestampMixin, models.Model):
    """An external URL that wants notifications about MADGA events.

    One row per (Site, URL) — a Site can have many endpoints, each
    subscribed to a different set of events.
    """

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="webhook_endpoints"
    )
    label = models.CharField(
        max_length=120, blank=True,
        help_text=_("Human-readable label, shown in the studio (e.g. 'aplica.do jobs sync')."),
    )
    url = models.URLField(max_length=500)
    events = models.JSONField(
        default=list, blank=True,
        help_text=_("List of event keys this endpoint subscribes to. Empty = all events."),
    )
    secret = models.CharField(
        max_length=64, default=_new_webhook_secret,
        help_text=_("Used to compute the X-Madga-Signature header on every delivery."),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="madga_webhook_endpoints",
    )

    # Cache for quick "what's the state?" rendering in the list view.
    last_fired_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    fail_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Webhook endpoint")
        verbose_name_plural = _("Webhook endpoints")

    def __str__(self) -> str:
        return f"{self.label or self.url} @ {self.site}"

    def matches(self, event: str) -> bool:
        """True if this endpoint should receive the given event."""
        if not self.events:
            return True  # empty list = subscribe to everything
        return event in self.events

    def rotate_secret(self) -> str:
        """Generate a new secret and persist it. Returns the new value."""
        self.secret = _new_webhook_secret()
        self.save(update_fields=["secret"])
        return self.secret


class WebhookDelivery(UUIDMixin, TimestampMixin, models.Model):
    """One attempt to deliver a single event to a single endpoint.

    A new row is created for each attempt. The sender updates
    ``response_status`` + ``response_body`` + ``finished_at`` when the
    HTTP call returns. ``retry_count`` increments on each retry; when
    it hits ``MADGA_WEBHOOK_MAX_RETRIES`` (default 5) the delivery is
    marked terminal-failed.
    """

    STATUS_PENDING = "pending"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_RETRY = "retry"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_RETRY, _("Retry scheduled")),
        (STATUS_DELIVERED, _("Delivered")),
        (STATUS_FAILED, _("Failed")),
    ]

    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries"
    )
    event = models.CharField(max_length=80, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
        ]
        verbose_name = _("Webhook delivery")
        verbose_name_plural = _("Webhook deliveries")

    def __str__(self) -> str:
        return f"{self.event} → {self.endpoint.url} ({self.status})"
