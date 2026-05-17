"""X (Twitter) publisher: OAuth 2.0 PKCE + v2 tweet endpoint.

Setup on developer.twitter.com:
    1. Create an OAuth 2.0 app under "User authentication settings"
    2. Type of App: "Web App, Automated App or Bot"
    3. App permissions: "Read and write"
    4. Callback URI: ``https://<your-site>/studio/channels/twitter/oauth/callback/``
    5. Copy Client ID + Client Secret into project settings::

        MADGA_OAUTH = {
            "twitter": {
                "client_id": "...",
                "client_secret": "...",
            },
        }

Then any studio user clicks "Connect" on the X channel card and
walks through the OAuth consent flow.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
import urllib.request

from django.utils.translation import gettext_lazy as _

from .base import CredField, register_publisher
from .social import _AccountPublisher, _http_post_form


@register_publisher
class TwitterOAuthPublisher(_AccountPublisher):
    """X (Twitter) publisher with real OAuth + tweet posting."""

    key = "twitter"
    label = _("X (Twitter)")
    description = _("Post to an X account with OAuth 2.0. Free tier: 100 writes/month.")
    icon = "send"
    char_limit = 280

    # OAuth-driven — no manual credential form rendered. The credentials
    # blob saved on PublisherAccount is populated by oauth_exchange.
    oauth_supported = True
    oauth_scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    credential_fields: list[CredField] = []

    setup_console_url = "https://developer.twitter.com/en/portal/dashboard"
    setup_instructions = [
        {
            "title": "Create a Project + App",
            "body": (
                "Sign in at developer.twitter.com. Create a new Project (or use an existing one). "
                "Inside the Project, create a new App. The free tier allows 100 posts per month, "
                "enough for most personal blogs."
            ),
            "url": "https://developer.twitter.com/en/portal/dashboard",
        },
        {
            "title": "Enable OAuth 2.0 with PKCE",
            "body": (
                "In your App settings → User authentication settings, click Set up. "
                "Pick: Type of App = Web App, App permissions = Read and write."
            ),
            "url": "",
        },
        {
            "title": "Add the callback URL",
            "body": (
                "Set Callback URI to:\n"
                "<copy>{CALLBACK}</copy>\n"
                "Website URL can be anything — your homepage works."
            ),
            "url": "",
        },
        {
            "title": "Copy Client ID + Client Secret",
            "body": (
                "After saving, you'll see Client ID + Client Secret. Copy both. "
                "The Secret is shown ONCE — keep it safe."
            ),
            "url": "",
        },
        {
            "title": "Add to your project's settings.py",
            "body": (
                "<copy>MADGA_OAUTH = {\n"
                "    'twitter': {\n"
                "        'client_id': 'PASTE_HERE',\n"
                "        'client_secret': 'PASTE_HERE',\n"
                "    },\n"
                "}</copy>\n"
                "Restart the server. The 'Needs setup' card will turn into a Connect button."
            ),
            "url": "",
        },
    ]

    AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    ME_URL = "https://api.twitter.com/2/users/me"
    TWEET_URL = "https://api.twitter.com/2/tweets"

    def _pkce_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _basic_auth_header(self) -> str:
        creds = self.oauth_client_credentials() or ("", "")
        cid, secret = creds
        token = base64.b64encode(f"{cid}:{secret}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def oauth_authorize_url(self, redirect_uri: str, state: str, pkce_verifier: str) -> str:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['twitter']['client_id'] is not configured")
        client_id, _ = creds
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.oauth_scopes),
            "state": state,
            "code_challenge": self._pkce_challenge(pkce_verifier),
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    def oauth_exchange(self, code: str, redirect_uri: str, pkce_verifier: str) -> dict:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['twitter'] is not configured")
        client_id, _ = creds

        token_resp = _http_post_form(
            self.TOKEN_URL,
            {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": pkce_verifier,
                "client_id": client_id,
            },
            headers={"Authorization": self._basic_auth_header()},
        )
        access_token = token_resp.get("access_token")
        if not access_token:
            raise RuntimeError(f"X token exchange returned no access_token: {token_resp}")

        # Look up the user so we can store the handle.
        req = urllib.request.Request(
            self.ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            me = json.loads(resp.read().decode("utf-8")).get("data", {})

        return {
            "credentials": {
                "access_token": access_token,
                "refresh_token": token_resp.get("refresh_token", ""),
                "expires_in": token_resp.get("expires_in", 0),
                "user_id": me.get("id", ""),
            },
            "handle": f"@{me.get('username', '')}" if me.get("username") else "",
            "display_name": me.get("name") or me.get("username") or "",
        }

    def _publish_one(self, job, account) -> None:
        creds = account.get_credentials()
        token = creds.get("access_token")
        if not token:
            raise RuntimeError("X account is missing access_token")

        text = job.body_text or self.default_copy(job)
        req = urllib.request.Request(
            self.TWEET_URL,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            json.loads(resp.read().decode("utf-8"))

    def test_connection(self, account) -> tuple[bool, str]:
        creds = account.get_credentials()
        token = creds.get("access_token")
        if not token:
            return False, "Missing access_token. Reconnect the account."
        try:
            req = urllib.request.Request(
                self.ME_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", {})
            return True, f"Authenticated as @{data.get('username', '?')}"
        except Exception as e:  # noqa: BLE001
            return False, f"X verify failed: {e}"
