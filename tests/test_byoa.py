"""Tests for BYOA: per-Site OAuth app credential overrides."""

import pytest
from django.test import Client, override_settings

from madga.models import Site, SiteOAuthApp, SiteUser
from madga.publishers import get_publisher


@pytest.fixture
def site(db):
    return Site.objects.create(name="Acme", domain="acme.local")


@pytest.fixture
def superuser(db, django_user_model):
    return django_user_model.objects.create_superuser("admin", "a@e.com", "p")


@pytest.fixture
def auth_client(superuser, site):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    c = Client()
    c.force_login(superuser)
    return c


@pytest.mark.django_db
def test_siteoauthapp_encrypts_secret_at_rest(site):
    app = SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter", client_id="ACME_CID",
    )
    app.set_secret("super-secret-token")
    app.save()
    app2 = SiteOAuthApp.objects.get(pk=app.pk)
    assert app2.get_secret() == "super-secret-token"
    assert "super-secret-token" not in app2._client_secret_enc


@override_settings(MADGA_OAUTH={})
@pytest.mark.django_db
def test_oauth_client_credentials_uses_site_override_when_present(site):
    SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter",
        client_id="ACME_TW", _client_secret_enc="",
    ).set_secret("S")
    twitter = get_publisher("twitter")
    creds = twitter.oauth_client_credentials(site=site)
    assert creds is not None
    cid, secret = creds
    assert cid == "ACME_TW"


@override_settings(MADGA_OAUTH={"twitter": {"client_id": "GLOBAL", "client_secret": "GSEC"}})
@pytest.mark.django_db
def test_site_override_beats_global_settings(site):
    app = SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter", client_id="OVR",
    )
    app.set_secret("OVR_SEC")
    app.save()
    twitter = get_publisher("twitter")
    cid, secret = twitter.oauth_client_credentials(site=site)
    assert cid == "OVR"
    assert secret == "OVR_SEC"


@override_settings(MADGA_OAUTH={"twitter": {"client_id": "GLOBAL", "client_secret": "GSEC"}})
@pytest.mark.django_db
def test_falls_back_to_global_when_no_site_override(site):
    twitter = get_publisher("twitter")
    cid, secret = twitter.oauth_client_credentials(site=site)
    assert cid == "GLOBAL"
    assert secret == "GSEC"


@override_settings(MADGA_OAUTH={})
@pytest.mark.django_db
def test_returns_none_when_neither_override_nor_global(site):
    twitter = get_publisher("twitter")
    assert twitter.oauth_client_credentials(site=site) is None
    assert twitter.oauth_client_credentials(site=None) is None


@pytest.mark.django_db
def test_byoa_view_creates_app(auth_client, site):
    r = auth_client.post("/studio/channels/twitter/byoa/", {
        "client_id": "ACME_TW_ID",
        "client_secret": "ACME_TW_SECRET",
        "notes": "Acme custom",
    })
    assert r.status_code == 302
    app = SiteOAuthApp.objects.get(site=site, publisher_key="twitter")
    assert app.client_id == "ACME_TW_ID"
    assert app.notes == "Acme custom"
    assert app.get_secret() == "ACME_TW_SECRET"


@pytest.mark.django_db
def test_byoa_view_edit_preserves_secret_if_blank(auth_client, site):
    """Submitting with empty client_secret should keep the stored one."""
    app = SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter", client_id="OLD",
    )
    app.set_secret("OLD_SEC")
    app.save()

    auth_client.post("/studio/channels/twitter/byoa/", {
        "client_id": "NEW_ID",
        "client_secret": "",  # blank → keep old
        "notes": "edited",
    })
    app.refresh_from_db()
    assert app.client_id == "NEW_ID"
    assert app.get_secret() == "OLD_SEC"


@pytest.mark.django_db
def test_byoa_view_empty_client_id_deletes_override(auth_client, site):
    """Submitting with empty client_id removes the override (revert to global)."""
    app = SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter", client_id="X",
    )
    auth_client.post("/studio/channels/twitter/byoa/", {
        "client_id": "",
        "client_secret": "",
        "notes": "",
    })
    assert not SiteOAuthApp.objects.filter(pk=app.pk).exists()


@override_settings(MADGA_OAUTH={})
@pytest.mark.django_db
def test_channels_page_shows_needs_setup_when_global_missing(auth_client, site):
    """No global config, no override → Needs setup card has setup/BYOA links."""
    r = auth_client.get("/studio/channels/")
    assert r.status_code == 200
    body = r.content.decode()
    # Language-agnostic: assert the actual URLs are linked from the card
    assert "/studio/channels/twitter/oauth/setup/" in body
    assert "/studio/channels/twitter/byoa/" in body


@override_settings(MADGA_OAUTH={})
@pytest.mark.django_db
def test_channels_page_no_needs_setup_after_byoa(auth_client, site):
    """With a Site override, the card no longer shows Needs setup."""
    app = SiteOAuthApp.objects.create(
        site=site, publisher_key="twitter", client_id="X",
    )
    app.set_secret("X")
    app.save()

    r = auth_client.get("/studio/channels/")
    body = r.content.decode()
    # Twitter card should show Connect button (not Needs setup)
    # We can't perfectly assert location-of-text in HTML, but at minimum
    # the card has a Connect link for twitter.
    assert 'href="/studio/channels/twitter/connect/' in body
