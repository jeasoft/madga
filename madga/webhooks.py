"""Webhook event firing + delivery worker.

Two entry points:

- :func:`fire_event` is what application code calls (or the signal
  handlers in :mod:`madga.signals` call). It looks up matching
  endpoints and creates ``WebhookDelivery`` rows.

- :func:`deliver_pending` is what the ``madga webhook-worker``
  management subcommand drives. It picks up pending/retry rows
  whose ``next_attempt_at`` is past and tries the HTTP POST.

A retry uses exponential backoff (60s, 5min, 30min, 2h, 12h) and
gives up after ``MADGA_WEBHOOK_MAX_RETRIES`` attempts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


def _max_retries() -> int:
    return int(getattr(settings, "MADGA_WEBHOOK_MAX_RETRIES", 5))


def _retry_delays() -> list[int]:
    """Backoff schedule in seconds. After the last one we mark failed."""
    return getattr(settings, "MADGA_WEBHOOK_RETRY_DELAYS", [
        60,        # 1 min
        5 * 60,    # 5 min
        30 * 60,   # 30 min
        2 * 60 * 60,   # 2 h
        12 * 60 * 60,  # 12 h
    ])


def _sign(secret: str, body: bytes, timestamp: int) -> str:
    """Compute ``t=<timestamp>,v1=<hex hmac>``.

    Receiver re-computes HMAC-SHA256 over ``f"{timestamp}.{body}"`` with
    the shared secret to verify authenticity + freshness (reject if
    timestamp is too old to prevent replay).
    """
    payload = f"{timestamp}.".encode("utf-8") + body
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def fire_event(site, event: str, payload: dict) -> int:
    """Create WebhookDelivery rows for every endpoint subscribed to ``event``.

    Returns the number of deliveries queued. Doesn't actually do the
    HTTP call — that's the worker's job. Safe to call from inside
    signal handlers; failures here never bubble up to the caller.
    """
    from madga.models import WebhookDelivery, WebhookEndpoint

    if site is None:
        return 0

    endpoints = WebhookEndpoint.objects.filter(site=site, is_active=True)
    if not endpoints.exists():
        return 0

    n = 0
    for ep in endpoints:
        if not ep.matches(event):
            continue
        try:
            WebhookDelivery.objects.create(
                endpoint=ep,
                event=event,
                payload=payload or {},
                next_attempt_at=timezone.now(),
            )
            n += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("webhook fire_event failed for %s: %s", ep.url, e)
    return n


def _deliver_one(delivery, dry_run: bool = False) -> bool:
    """POST the delivery's payload to its endpoint. Returns True on 2xx.

    Updates the delivery row + endpoint cache fields. Exceptions are
    caught and stored as ``delivery.error``.
    """
    ep = delivery.endpoint
    body = json.dumps({
        "id": str(delivery.id),
        "event": delivery.event,
        "created_at": delivery.created_at.isoformat(),
        "data": delivery.payload,
    }, default=str, ensure_ascii=False).encode("utf-8")

    ts = int(time.time())
    signature = _sign(ep.secret, body, ts)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MADGA-Webhooks/1.0",
        "X-Madga-Event": delivery.event,
        "X-Madga-Delivery": str(delivery.id),
        "X-Madga-Signature": signature,
        "X-Madga-Timestamp": str(ts),
    }

    if dry_run:
        delivery.response_status = 200
        delivery.response_body = "(dry-run)"
        delivery.status = delivery.STATUS_DELIVERED
        delivery.finished_at = timezone.now()
        delivery.save(update_fields=[
            "response_status", "response_body", "status", "finished_at",
        ])
        return True

    req = urllib.request.Request(ep.url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            text = resp.read(2048).decode("utf-8", errors="replace")
        ok = 200 <= status < 300
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            text = e.read(2048).decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            text = str(e)
        ok = False
    except Exception as e:  # noqa: BLE001
        status = 0
        text = str(e)
        ok = False

    delivery.response_status = status
    delivery.response_body = (text or "")[:4000]
    delivery.finished_at = timezone.now()

    if ok:
        delivery.status = delivery.STATUS_DELIVERED
        delivery.error = ""
        ep.last_fired_at = timezone.now()
        ep.last_response_status = status
        ep.last_error = ""
        ep.fail_count = 0
        ep.save(update_fields=["last_fired_at", "last_response_status", "last_error", "fail_count"])
        delivery.save(update_fields=["response_status", "response_body", "finished_at", "status", "error"])
        return True

    # Failure path: schedule retry or mark terminal failed.
    delivery.retry_count += 1
    delays = _retry_delays()
    if delivery.retry_count >= _max_retries():
        delivery.status = delivery.STATUS_FAILED
        delivery.next_attempt_at = None
        ep.last_fired_at = timezone.now()
        ep.last_response_status = status
        ep.last_error = (text or "")[:2000]
        ep.fail_count = (ep.fail_count or 0) + 1
        ep.save(update_fields=["last_fired_at", "last_response_status", "last_error", "fail_count"])
    else:
        delay = delays[min(delivery.retry_count - 1, len(delays) - 1)]
        delivery.status = delivery.STATUS_RETRY
        delivery.next_attempt_at = timezone.now() + timedelta(seconds=delay)

    delivery.error = (text or "")[:2000]
    delivery.save(update_fields=[
        "response_status", "response_body", "finished_at", "status",
        "retry_count", "next_attempt_at", "error",
    ])
    return False


def deliver_pending(limit: int = 100, dry_run: bool = False) -> int:
    """Run a single pass of the delivery worker.

    Picks up to ``limit`` pending or due-for-retry rows ordered by
    creation time and POSTs each. Returns the number of attempts
    made (not the number of successes).
    """
    from madga.models import WebhookDelivery

    now = timezone.now()
    qs = WebhookDelivery.objects.filter(
        status__in=(WebhookDelivery.STATUS_PENDING, WebhookDelivery.STATUS_RETRY),
        next_attempt_at__lte=now,
    ).select_related("endpoint").order_by("created_at")[:limit]
    n = 0
    for d in qs:
        _deliver_one(d, dry_run=dry_run)
        n += 1
    return n
