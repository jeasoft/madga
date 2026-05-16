"""Tests for PublisherAccount + encryption + Channels UI."""

import pytest
from django.test import Client

from madga.encryption import decrypt, encrypt, safe_decrypt
from madga.models import PublisherAccount, Site, SiteUser
from madga.publishers import all_publishers, get_publisher


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test Site", domain="localhost")


@pytest.fixture
def superuser(db, django_user_model):
    return django_user_model.objects.create_superuser("admin", "admin@ex.com", "pw")


@pytest.fixture
def auth_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip():
    plain = "very-secret-token-12345"
    cipher = encrypt(plain)
    assert cipher != plain
    assert decrypt(cipher) == plain


def test_safe_decrypt_returns_default_on_failure():
    assert safe_decrypt("not-valid-ciphertext", default="X") == "X"
    assert safe_decrypt("", default="") == ""
    assert safe_decrypt(None, default="oh") == "oh"


# ---------------------------------------------------------------------------
# PublisherAccount model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_publisher_account_credentials_roundtrip(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    acct.set_credentials({"api_key": "abc", "api_secret": "xyz"})
    acct.save()

    acct2 = PublisherAccount.objects.get(pk=acct.pk)
    assert acct2.get_credentials() == {"api_key": "abc", "api_secret": "xyz"}
    # Raw column is encrypted, not plaintext
    assert "abc" not in acct2._credentials_enc
    assert "xyz" not in acct2._credentials_enc


@pytest.mark.django_db
def test_publisher_account_pause_resume(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
        last_error="something failed",
    )
    acct.pause()
    acct.refresh_from_db()
    assert acct.is_active is False
    acct.resume()
    acct.refresh_from_db()
    assert acct.is_active is True
    assert acct.last_error == ""


# ---------------------------------------------------------------------------
# Publisher.is_configured(site)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_account_driven_publishers_unconfigured_without_account(site):
    """OAuth-supported publishers (no credential_fields) also need an account."""
    twitter = get_publisher("twitter")
    assert twitter is not None
    assert twitter.is_configured() is False     # no site
    assert twitter.is_configured(site) is False  # site but no account
    # Also Mastodon (credential-fields-driven)
    mastodon = get_publisher("mastodon")
    assert mastodon.is_configured(site) is False


@pytest.mark.django_db
def test_account_driven_publisher_configured_with_active_account(site):
    PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    twitter = get_publisher("twitter")
    assert twitter.is_configured(site) is True


@pytest.mark.django_db
def test_paused_account_does_not_make_publisher_configured(site):
    PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=False,
    )
    twitter = get_publisher("twitter")
    assert twitter.is_configured(site) is False


@pytest.mark.django_db
def test_all_publishers_filters_by_site(site):
    PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    configured = all_publishers(only_configured=True, site=site)
    keys = [p.key for p in configured]
    # email_subscribers always counts, twitter counts because account exists
    assert "email_subscribers" in keys
    assert "twitter" in keys
    # other stubs without accounts are filtered out
    assert "linkedin" not in keys
    assert "mastodon" not in keys


# ---------------------------------------------------------------------------
# Publisher default_copy
# ---------------------------------------------------------------------------

class _Job:
    """Lightweight stand-in for BroadcastJob."""
    def __init__(self, subject="", related_url=""):
        self.subject = subject
        self.related_url = related_url


def test_default_copy_under_limit_returns_full_text():
    twitter = get_publisher("twitter")
    job = _Job(subject="Hi", related_url="https://x.com/post/1")
    text = twitter.default_copy(job)
    assert "Hi" in text
    assert "https://x.com/post/1" in text


def test_default_copy_truncates_to_char_limit():
    twitter = get_publisher("twitter")  # 280 char limit
    job = _Job(subject="A" * 500, related_url="https://example.com/p")
    text = twitter.default_copy(job)
    assert len(text) <= twitter.char_limit
    # URL preserved
    assert "https://example.com/p" in text


# ---------------------------------------------------------------------------
# Channels page + connect/disconnect/toggle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_channel_list_renders(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    response = auth_client.get("/studio/channels/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Channels" in body or "Canales" in body
    # Every account-driven stub publisher should appear
    assert "Twitter" in body or "X" in body
    assert "Mastodon" in body
    assert "Bluesky" in body
    assert "LinkedIn" in body


@pytest.mark.django_db
def test_channel_connect_stores_encrypted_credentials(site, superuser, auth_client):
    """Manual connect flow stores credentials encrypted (Mastodon = manual)."""
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    response = auth_client.post("/studio/channels/mastodon/connect/", {
        "handle": "@aitorruiz@hachyderm.io",
        "display_name": "Aitor Ruiz",
        "instance_url": "https://hachyderm.io",
        "access_token": "T-secret-token",
    })
    assert response.status_code == 302
    acct = PublisherAccount.objects.get(site=site, publisher_key="mastodon", handle="@aitorruiz@hachyderm.io")
    assert acct.is_active
    creds = acct.get_credentials()
    assert creds["instance_url"] == "https://hachyderm.io"
    assert creds["access_token"] == "T-secret-token"
    # Ciphertext doesn't contain plaintext
    assert "T-secret-token" not in acct._credentials_enc


@pytest.mark.django_db
def test_oauth_connect_for_twitter_redirects_to_oauth_start(site, superuser, auth_client):
    """GET /channels/twitter/connect/ for OAuth-supported should redirect to /oauth/start/."""
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    response = auth_client.get("/studio/channels/twitter/connect/")
    assert response.status_code == 302
    assert "/oauth/start/" in response["Location"]


@pytest.mark.django_db
def test_channel_toggle_pauses_and_resumes(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    auth_client.post(f"/studio/channels/{acct.pk}/toggle/")
    acct.refresh_from_db()
    assert acct.is_active is False
    auth_client.post(f"/studio/channels/{acct.pk}/toggle/")
    acct.refresh_from_db()
    assert acct.is_active is True


@pytest.mark.django_db
def test_channel_disconnect_deletes_account(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    auth_client.post(f"/studio/channels/{acct.pk}/disconnect/")
    assert not PublisherAccount.objects.filter(pk=acct.pk).exists()


@pytest.mark.django_db
def test_test_connection_fails_when_creds_missing(site):
    """For OAuth-supported publishers, missing access_token = clear error."""
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    acct.set_credentials({})
    acct.save()
    pub = get_publisher("twitter")
    ok, msg = pub.test_connection(acct)
    assert ok is False
    assert "access_token" in msg.lower() or "reconnect" in msg.lower()


@pytest.mark.django_db
def test_email_publisher_test_connection_succeeds_with_console_backend():
    pub = get_publisher("email_subscribers")
    ok, msg = pub.test_connection()
    assert ok is True
    assert "reachable" in msg.lower()


@pytest.mark.django_db
def test_channel_test_view_records_failure_on_error(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="instagram", handle="@aplica", is_active=True,
    )
    # No credentials saved — should fail
    response = auth_client.post(f"/studio/channels/{acct.pk}/test/")
    assert response.status_code == 302
    acct.refresh_from_db()
    assert acct.last_error  # error was recorded


# ---------------------------------------------------------------------------
# Workspace switcher + create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_workspace_switch_pins_active_site(site, superuser, auth_client, db):
    other = Site.objects.create(name="Other", domain="other.local")
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    SiteUser.objects.create(site=other, user=superuser, role=SiteUser.ROLE_OWNER)
    auth_client.post("/studio/workspaces/switch/", {"site_id": str(other.id)})
    response = auth_client.get("/studio/dashboard/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_workspace_create_makes_user_owner(superuser, auth_client, db):
    response = auth_client.post("/studio/workspaces/new/", {
        "name": "My Company",
        "domain": "my-company.test",
    })
    assert response.status_code == 302
    site = Site.objects.get(domain="my-company.test")
    assert SiteUser.objects.filter(
        site=site, user=superuser, role=SiteUser.ROLE_OWNER
    ).exists()
