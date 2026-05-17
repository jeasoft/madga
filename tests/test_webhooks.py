"""Tests for outbound webhooks: signing, fire_event, deliver_pending."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from madga.models import Post, Site, WebhookDelivery, WebhookEndpoint
from madga.webhooks import _sign, deliver_pending, fire_event


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test", domain="localhost")


@pytest.fixture
def endpoint(site):
    return WebhookEndpoint.objects.create(
        site=site, url="https://example.com/hook", label="t",
        events=["post.published"], is_active=True,
    )


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def test_sign_format_is_stripe_style():
    sig = _sign("secret", b'{"x":1}', 1700000000)
    assert sig.startswith("t=1700000000,v1=")
    # Receiver-compatible recompute
    expected = hmac.new(b"secret", b"1700000000.{\"x\":1}", hashlib.sha256).hexdigest()
    assert sig == f"t=1700000000,v1={expected}"


# ---------------------------------------------------------------------------
# fire_event
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fire_event_creates_delivery_for_matching_endpoint(site, endpoint):
    n = fire_event(site, "post.published", {"id": "abc"})
    assert n == 1
    d = WebhookDelivery.objects.get()
    assert d.endpoint == endpoint
    assert d.event == "post.published"
    assert d.payload == {"id": "abc"}
    assert d.status == WebhookDelivery.STATUS_PENDING


@pytest.mark.django_db
def test_fire_event_skips_unsubscribed_endpoint(site, endpoint):
    # endpoint only subscribes to post.published
    n = fire_event(site, "post.deleted", {"x": "y"})
    assert n == 0
    assert WebhookDelivery.objects.count() == 0


@pytest.mark.django_db
def test_fire_event_with_empty_events_means_all(site):
    WebhookEndpoint.objects.create(
        site=site, url="https://x.example/hook",
        events=[], is_active=True,
    )
    n = fire_event(site, "subscriber.created", {"email": "a@e.com"})
    assert n == 1


@pytest.mark.django_db
def test_fire_event_skips_paused_endpoint(site, endpoint):
    endpoint.is_active = False
    endpoint.save()
    n = fire_event(site, "post.published", {})
    assert n == 0


@pytest.mark.django_db
def test_fire_event_with_no_site_returns_zero():
    assert fire_event(None, "x.y", {}) == 0


# ---------------------------------------------------------------------------
# deliver_pending
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deliver_pending_posts_payload_and_marks_delivered(endpoint):
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint, event="post.published",
        payload={"id": "abc"},
    )
    from django.utils import timezone
    delivery.next_attempt_at = timezone.now()
    delivery.save()

    with patch("madga.webhooks.urllib.request.urlopen") as mock_open:
        resp = MagicMock()
        resp.__enter__ = lambda self: resp
        resp.__exit__ = lambda *a: None
        resp.status = 200
        resp.read.return_value = b"OK"
        mock_open.return_value = resp

        n = deliver_pending(limit=10)

    assert n == 1
    delivery.refresh_from_db()
    assert delivery.status == WebhookDelivery.STATUS_DELIVERED
    assert delivery.response_status == 200

    # POST went to the right URL with signature
    args, _ = mock_open.call_args
    req = args[0]
    assert req.full_url == "https://example.com/hook"
    assert req.headers.get("X-madga-signature", "").startswith("t=")


@pytest.mark.django_db
def test_deliver_pending_retries_on_5xx(endpoint):
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint, event="post.published", payload={},
    )
    from django.utils import timezone
    delivery.next_attempt_at = timezone.now()
    delivery.save()

    with patch("madga.webhooks.urllib.request.urlopen") as mock_open:
        import urllib.error
        mock_open.side_effect = urllib.error.HTTPError(
            "https://example.com/hook", 500, "Server Error", {}, MagicMock(read=lambda *a: b"err"),
        )
        deliver_pending(limit=10)

    delivery.refresh_from_db()
    assert delivery.status == WebhookDelivery.STATUS_RETRY
    assert delivery.retry_count == 1
    assert delivery.next_attempt_at is not None


@pytest.mark.django_db
def test_deliver_pending_marks_failed_after_max_retries(endpoint, settings):
    settings.MADGA_WEBHOOK_MAX_RETRIES = 2

    from django.utils import timezone
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint, event="post.published", payload={},
        retry_count=1,
        next_attempt_at=timezone.now(),
    )

    with patch("madga.webhooks.urllib.request.urlopen") as mock_open:
        import urllib.error
        mock_open.side_effect = urllib.error.HTTPError(
            "x", 500, "x", {}, MagicMock(read=lambda *a: b""),
        )
        deliver_pending(limit=10)

    delivery.refresh_from_db()
    assert delivery.status == WebhookDelivery.STATUS_FAILED
    assert delivery.retry_count == 2


@pytest.mark.django_db
def test_dry_run_marks_delivered_without_http_call(endpoint):
    from django.utils import timezone
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint, event="post.published", payload={},
        next_attempt_at=timezone.now(),
    )
    n = deliver_pending(limit=10, dry_run=True)
    assert n == 1
    delivery.refresh_from_db()
    assert delivery.status == WebhookDelivery.STATUS_DELIVERED


# ---------------------------------------------------------------------------
# Signal integration: post.published fires the event
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_post_published_signal_creates_webhook_delivery(site, endpoint, django_user_model):
    user = django_user_model.objects.create_user("a", "a@e.com", "p")
    post = Post.objects.create(
        site=site, title="Hi", status=Post.STATUS_DRAFT, author=user,
    )
    # No delivery yet — only post.updated fires on create
    assert WebhookDelivery.objects.filter(event="post.published").count() == 0

    post.status = Post.STATUS_PUBLISHED
    post.save()

    assert WebhookDelivery.objects.filter(event="post.published").count() == 1
    d = WebhookDelivery.objects.filter(event="post.published").first()
    assert d.payload["title"] == "Hi"
