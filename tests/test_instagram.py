"""Tests for InstagramOAuthPublisher: OAuth dance + two-step publish."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from madga.models import BroadcastJob, MediaFile, Post, PublisherAccount, Site
from madga.publishers import get_publisher


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test", domain="my-site.com")


@pytest.fixture
def post_with_image(site, db, django_user_model):
    user = django_user_model.objects.create_user("a", "a@e.com", "p")
    media = MediaFile.objects.create(
        site=site, file_type="image", filename="hero.png",
    )
    # No real file; just attach the path so .file.url returns something.
    media.file.name = "madga/media/2026/05/hero.png"
    media.save()
    post = Post.objects.create(
        site=site, title="Hello", status=Post.STATUS_PUBLISHED,
        author=user, featured_image=media,
    )
    return post


@pytest.mark.django_db
def test_instagram_publisher_is_registered_and_oauth_supported():
    pub = get_publisher("instagram")
    assert pub is not None
    assert pub.oauth_supported is True
    assert "instagram_content_publish" in pub.oauth_scopes
    assert pub.char_limit == 2200


def test_instagram_authorize_url_includes_required_scopes(settings):
    settings.MADGA_OAUTH = {"instagram": {"client_id": "FB_APP", "client_secret": "x"}}
    pub = get_publisher("instagram")
    url = pub.oauth_authorize_url(
        "https://my.app/cb/", "STATE", "VERIFIER",
    )
    assert "facebook.com" in url
    assert "client_id=FB_APP" in url
    assert "instagram_basic" in url
    assert "instagram_content_publish" in url
    assert "pages_show_list" in url


@pytest.mark.django_db
def test_instagram_publish_requires_image(site):
    """Without a featured image, publish should fail with a clear error."""
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="instagram", handle="@me", is_active=True,
    )
    acct.set_credentials({
        "ig_user_id": "1234",
        "page_access_token": "PAGE_T",
    })
    acct.save()

    job = BroadcastJob.objects.create(
        site=site, publisher_key="instagram",
        subject="Hi", body_text="Hi IG",
        related_post=None, targets_count=1,
    )
    pub = get_publisher("instagram")
    result = pub.publish(job)
    assert result.failed == 1
    assert "image" in result.errors[0]["msg"].lower()


@pytest.mark.django_db
def test_instagram_publish_rejects_localhost_image(site, post_with_image):
    """IG fetches the URL — localhost will never work, fail fast."""
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="instagram", handle="@me", is_active=True,
    )
    acct.set_credentials({"ig_user_id": "1234", "page_access_token": "PAGE_T"})
    acct.save()

    job = BroadcastJob.objects.create(
        site=site, publisher_key="instagram",
        subject="Hi", body_text="Hi IG",
        related_post=post_with_image, targets_count=1,
    )
    # Override site.domain to localhost so the image URL resolves to http://localhost/...
    post_with_image.site.domain = "localhost"
    post_with_image.site.save()
    job.site = post_with_image.site

    pub = get_publisher("instagram")
    result = pub.publish(job)
    assert result.failed == 1
    assert "localhost" in result.errors[0]["msg"].lower()


@pytest.mark.django_db
def test_instagram_publish_does_two_step_create_then_publish(site, post_with_image):
    """Happy path: create_container → media_publish, both mocked."""
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="instagram", handle="@me", is_active=True,
    )
    acct.set_credentials({"ig_user_id": "IG_USER", "page_access_token": "PAGE_T"})
    acct.save()

    job = BroadcastJob.objects.create(
        site=site, publisher_key="instagram",
        subject="Hi", body_text="Hi IG",
        related_post=post_with_image, targets_count=1,
    )

    pub = get_publisher("instagram")
    with patch("madga.publishers.instagram._http_post_form") as mock_post:
        mock_post.side_effect = [
            {"id": "CONTAINER_ID"},   # step 1
            {"id": "MEDIA_ID"},       # step 2
        ]
        result = pub.publish(job)

    assert result.sent == 1
    assert mock_post.call_count == 2
    # Step 1 hits /media with image_url + caption
    args1 = mock_post.call_args_list[0]
    assert "/IG_USER/media" in args1[0][0]
    assert args1[0][1]["caption"] == "Hi IG"
    assert args1[0][1]["image_url"].startswith("http")
    assert args1[0][1]["access_token"] == "PAGE_T"
    # Step 2 hits /media_publish with creation_id
    args2 = mock_post.call_args_list[1]
    assert "/IG_USER/media_publish" in args2[0][0]
    assert args2[0][1]["creation_id"] == "CONTAINER_ID"


@pytest.mark.django_db
def test_instagram_test_connection_hits_graph_api(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="instagram", handle="@aplica", is_active=True,
    )
    acct.set_credentials({"ig_user_id": "IG1", "page_access_token": "PT"})
    acct.save()

    pub = get_publisher("instagram")
    with patch("madga.publishers.instagram.urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda self: mock_resp
        mock_resp.__exit__ = lambda *a: None
        mock_resp.read.return_value = b'{"username": "aplica", "followers_count": 1234}'
        mock_urlopen.return_value = mock_resp

        ok, msg = pub.test_connection(acct)
    assert ok is True
    assert "@aplica" in msg
    assert "1234" in msg


@pytest.mark.django_db
def test_instagram_oauth_exchange_picks_page_with_ig_attached(site, settings):
    """Walk through the FB OAuth callback dance:
    short-lived → long-lived → /me/accounts → page detail → IG username.
    """
    settings.MADGA_OAUTH = {"instagram": {"client_id": "APP", "client_secret": "SEC"}}
    pub = get_publisher("instagram")

    with patch("madga.publishers.instagram.urllib.request.urlopen") as mock_urlopen:
        def fake_open(url, timeout=None):
            url_str = url if isinstance(url, str) else getattr(url, "full_url", "")
            resp = MagicMock()
            resp.__enter__ = lambda self: resp
            resp.__exit__ = lambda *a: None
            if "fb_exchange_token" in url_str:
                resp.read.return_value = b'{"access_token": "LONG_LIVED"}'
            elif "oauth/access_token" in url_str:
                resp.read.return_value = b'{"access_token": "SHORT"}'
            elif "/me/accounts" in url_str:
                resp.read.return_value = json.dumps({
                    "data": [
                        {"id": "PAGE_A", "access_token": "PAGEA_TOKEN"},
                    ],
                }).encode()
            elif "PAGE_A?fields=instagram_business_account" in url_str:
                resp.read.return_value = json.dumps({
                    "instagram_business_account": {"id": "IG_BIZ"},
                    "name": "Acme Page",
                }).encode()
            elif "IG_BIZ?fields=username" in url_str:
                resp.read.return_value = b'{"username": "acmeofficial"}'
            else:
                resp.read.return_value = b'{}'
            return resp
        mock_urlopen.side_effect = fake_open

        result = pub.oauth_exchange("THECODE", "https://my.app/cb/", "")

    assert result["handle"] == "@acmeofficial"
    creds = result["credentials"]
    assert creds["ig_user_id"] == "IG_BIZ"
    assert creds["page_access_token"] == "PAGEA_TOKEN"
    assert creds["user_access_token"] == "LONG_LIVED"
