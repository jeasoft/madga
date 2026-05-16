"""Tests for the OAuth start/callback flow + Twitter + LinkedIn publishers."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, override_settings

from madga.models import PublisherAccount, Site, SiteUser
from madga.publishers import get_publisher


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test", domain="localhost")


@pytest.fixture
def superuser(db, django_user_model):
    return django_user_model.objects.create_superuser("admin", "a@e.com", "p")


@pytest.fixture
def auth_client(superuser, site, db):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    c = Client()
    c.force_login(superuser)
    return c


# ---------------------------------------------------------------------------
# OAuth start
# ---------------------------------------------------------------------------

@override_settings(MADGA_OAUTH={
    "twitter": {"client_id": "TWT_ID", "client_secret": "TWT_SECRET"},
})
def test_oauth_start_redirects_to_twitter_authorize_url(auth_client):
    response = auth_client.get("/studio/channels/twitter/oauth/start/")
    assert response.status_code == 302
    location = response["Location"]
    assert "twitter.com/i/oauth2/authorize" in location
    assert "client_id=TWT_ID" in location
    assert "code_challenge_method=S256" in location
    # Session should have stored state + verifier for the callback to validate
    s = auth_client.session
    assert s.get("madga_oauth_state_twitter")
    assert s.get("madga_oauth_pkce_twitter")


def test_oauth_start_without_settings_flashes_error(auth_client):
    # No MADGA_OAUTH set
    response = auth_client.get("/studio/channels/twitter/oauth/start/")
    assert response.status_code == 302
    assert "/studio/channels/" in response["Location"]


@override_settings(MADGA_OAUTH={
    "linkedin": {"client_id": "LI_ID", "client_secret": "LI_SECRET"},
})
def test_oauth_start_for_linkedin(auth_client):
    response = auth_client.get("/studio/channels/linkedin/oauth/start/")
    assert response.status_code == 302
    assert "linkedin.com/oauth/v2/authorization" in response["Location"]
    assert "client_id=LI_ID" in response["Location"]


# ---------------------------------------------------------------------------
# OAuth callback (Twitter)
# ---------------------------------------------------------------------------

@override_settings(MADGA_OAUTH={
    "twitter": {"client_id": "TWT_ID", "client_secret": "TWT_SECRET"},
})
@pytest.mark.django_db
def test_oauth_callback_creates_account_on_success(auth_client, site):
    # Seed session with state + verifier as if /start/ ran
    session = auth_client.session
    session["madga_oauth_state_twitter"] = "STATE-1"
    session["madga_oauth_pkce_twitter"] = "VERIFIER-1"
    session.save()

    with patch("madga.publishers.twitter._http_post_form") as mock_token, \
         patch("madga.publishers.twitter.urllib.request.urlopen") as mock_urlopen:
        mock_token.return_value = {
            "access_token": "AT", "refresh_token": "RT", "expires_in": 7200,
        }
        # /2/users/me response
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda self: mock_resp
        mock_resp.__exit__ = lambda *a: None
        mock_resp.read.return_value = b'{"data": {"id": "123", "username": "aitorruiz", "name": "Aitor"}}'
        mock_urlopen.return_value = mock_resp

        response = auth_client.get(
            "/studio/channels/twitter/oauth/callback/?code=THE-CODE&state=STATE-1"
        )
    assert response.status_code == 302
    acct = PublisherAccount.objects.get(site=site, publisher_key="twitter")
    assert acct.is_active
    assert acct.handle == "@aitorruiz"
    creds = acct.get_credentials()
    assert creds["access_token"] == "AT"
    assert creds["refresh_token"] == "RT"
    assert creds["user_id"] == "123"


@pytest.mark.django_db
def test_oauth_callback_state_mismatch_rejects(auth_client, site):
    session = auth_client.session
    session["madga_oauth_state_twitter"] = "EXPECTED"
    session["madga_oauth_pkce_twitter"] = "X"
    session.save()
    response = auth_client.get(
        "/studio/channels/twitter/oauth/callback/?code=X&state=WRONG"
    )
    assert response.status_code == 302
    assert not PublisherAccount.objects.filter(publisher_key="twitter").exists()


@pytest.mark.django_db
def test_oauth_callback_handles_error_from_platform(auth_client, site):
    session = auth_client.session
    session["madga_oauth_state_twitter"] = "X"
    session.save()
    response = auth_client.get(
        "/studio/channels/twitter/oauth/callback/?error=access_denied"
    )
    assert response.status_code == 302
    assert not PublisherAccount.objects.filter(publisher_key="twitter").exists()


# ---------------------------------------------------------------------------
# Twitter + LinkedIn publish()
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_twitter_publish_calls_tweets_endpoint(site):
    from madga.models import BroadcastJob
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="twitter", handle="@me", is_active=True,
    )
    acct.set_credentials({"access_token": "AT"})
    acct.save()
    job = BroadcastJob.objects.create(
        site=site, publisher_key="twitter",
        subject="Hi", body_text="Hi from MADGA",
        targets_count=1,
    )

    pub = get_publisher("twitter")
    with patch("madga.publishers.twitter.urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda self: mock_resp
        mock_resp.__exit__ = lambda *a: None
        mock_resp.read.return_value = b'{"data": {"id": "999"}}'
        mock_urlopen.return_value = mock_resp
        result = pub.publish(job)

    assert result.sent == 1
    args, _ = mock_urlopen.call_args
    request = args[0]
    assert request.full_url == "https://api.twitter.com/2/tweets"
    assert request.headers.get("Authorization") == "Bearer AT"


@pytest.mark.django_db
def test_linkedin_publish_calls_ugcposts(site):
    from madga.models import BroadcastJob
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="linkedin", handle="me@example.com", is_active=True,
    )
    acct.set_credentials({"access_token": "AT", "person_urn": "urn:li:person:abc"})
    acct.save()
    job = BroadcastJob.objects.create(
        site=site, publisher_key="linkedin",
        subject="Hi", body_text="Hi LinkedIn",
        targets_count=1,
    )

    pub = get_publisher("linkedin")
    with patch("madga.publishers.linkedin.urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda self: mock_resp
        mock_resp.__exit__ = lambda *a: None
        mock_resp.read.return_value = b''
        mock_urlopen.return_value = mock_resp
        result = pub.publish(job)

    assert result.sent == 1
    args, _ = mock_urlopen.call_args
    request = args[0]
    assert request.full_url == "https://api.linkedin.com/v2/ugcPosts"
    assert request.headers.get("Authorization") == "Bearer AT"
