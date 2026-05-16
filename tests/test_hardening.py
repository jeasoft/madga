"""Tests for the 0.3.3 production hardening additions."""

import io

import pytest
from django.conf import settings
from django.test import Client, override_settings
from PIL import Image

from madga.models import MediaFile, Site


@pytest.fixture
def site(db):
    return Site.objects.create(
        name="Test Site", domain="localhost", accent_color="#6C63FF",
        google_analytics_id="G-XXXX",
    )


@pytest.fixture
def site_no_tracker(db):
    return Site.objects.create(name="Plain", domain="localhost")


@pytest.fixture
def image_bytes():
    """A small valid PNG to upload."""
    buf = io.BytesIO()
    Image.new("RGB", (1200, 800), color="red").save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------

@override_settings(DEBUG=False, ALLOWED_HOSTS=["*"])
def test_404_renders_madga_template(db, client):
    site = Site.objects.create(name="X", domain="localhost", is_active=True)
    response = client.get("/this-path-definitely-doesnt-exist-9k3j2/")
    assert response.status_code == 404
    body = response.content.decode()
    assert "We couldn't find that." in body or "Page not found" in body or "404" in body


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

@override_settings(DEBUG=False, ALLOWED_HOSTS=["*"], MADGA_SECURITY_FORCE=True)
def test_security_headers_emitted_in_prod(db, client):
    Site.objects.create(name="X", domain="localhost", is_active=True)
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


@override_settings(DEBUG=True)
def test_security_headers_skipped_in_debug(db, client):
    Site.objects.create(name="X", domain="localhost", is_active=True)
    response = client.get("/")
    # Without MADGA_SECURITY_FORCE, middleware is a no-op in DEBUG
    assert "Strict-Transport-Security" not in response.headers


# ---------------------------------------------------------------------------
# Cookie banner + tracking gating
# ---------------------------------------------------------------------------

def test_cookie_banner_shows_when_tracker_configured_and_no_consent(site, client):
    response = client.get("/")
    body = response.content.decode()
    assert "madga-cookie-banner" in body
    assert "We use cookies" in body or "Usamos cookies" in body or "cookies" in body.lower()


def test_cookie_banner_hidden_without_trackers(site_no_tracker, client):
    response = client.get("/")
    body = response.content.decode()
    assert "madga-cookie-banner" not in body


def test_cookie_banner_hidden_after_consent_accepted(site, client):
    client.cookies["madga_consent"] = "accepted"
    response = client.get("/")
    body = response.content.decode()
    assert "madga-cookie-banner" not in body


def test_cookie_banner_hidden_after_consent_declined(site, client):
    client.cookies["madga_consent"] = "declined"
    response = client.get("/")
    body = response.content.decode()
    assert "madga-cookie-banner" not in body


def test_tracking_does_not_fire_without_consent(site, client):
    response = client.get("/")
    body = response.content.decode()
    assert "googletagmanager.com" not in body


def test_tracking_fires_after_consent(site, client):
    client.cookies["madga_consent"] = "accepted"
    response = client.get("/")
    body = response.content.decode()
    assert "googletagmanager.com" in body


# ---------------------------------------------------------------------------
# Image optimization
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_image_optimization_generates_webp_variants(site, image_bytes, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)

    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("test.png", image_bytes.read(), content_type="image/png")
    media = MediaFile.objects.create(
        site=site,
        file=upload,
        file_type="image",
        filename="test.png",
        mime_type="image/png",
        size=len(image_bytes.getvalue()),
    )
    media.refresh_from_db()

    assert media.variants, f"Expected variants populated, got {media.variants!r}"
    # Source is 1200px wide. sm (480) and md (960) fit under source → emitted.
    # lg (1440) would upscale → skipped. xl is always emitted, capped at source width.
    assert "sm" in media.variants
    assert "md" in media.variants
    assert "lg" not in media.variants  # would have upscaled — skipped
    assert "xl" in media.variants
    assert media.variants["xl"]["width"] == 1200  # capped at source
    for key, v in media.variants.items():
        assert v["format"] == "webp"
        assert v["width"] > 0
        assert v["url"].endswith(".webp")


@pytest.mark.django_db
def test_mediafile_srcset_returns_comma_separated_string(site):
    media = MediaFile.objects.create(
        site=site, file_type="image", filename="x.png",
        variants={
            "sm": {"url": "/media/x.sm.webp", "width": 480, "height": 320, "format": "webp"},
            "lg": {"url": "/media/x.lg.webp", "width": 1440, "height": 960, "format": "webp"},
        },
    )
    s = media.srcset()
    assert "480w" in s
    assert "1440w" in s
    assert "," in s


@pytest.mark.django_db
def test_mediafile_srcset_falls_back_to_original(site):
    from django.core.files.uploadedfile import SimpleUploadedFile
    upload = SimpleUploadedFile("y.png", b"x", content_type="image/png")
    media = MediaFile.objects.create(
        site=site, file=upload, file_type="other", filename="y.png", variants={},
    )
    # file_type=other → no variants; srcset returns original URL string
    assert media.srcset() == media.file.url or media.srcset() == ""
