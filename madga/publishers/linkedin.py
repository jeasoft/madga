"""LinkedIn publisher: OAuth 2.0 + UGC Post API.

Setup on linkedin.com/developers:
    1. Create an app, request access to "Share on LinkedIn" + "Sign In with LinkedIn"
       products
    2. Add OAuth 2.0 redirect URL:
       ``https://<your-site>/studio/channels/linkedin/oauth/callback/``
    3. Copy Client ID + Client Secret into project settings::

        MADGA_OAUTH = {
            "linkedin": {
                "client_id": "...",
                "client_secret": "...",
            },
        }

Tokens last ~60 days. Users will need to re-connect when the token
expires — we surface a clear last_error when an API call fails 401.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from django.utils.translation import gettext_lazy as _

from .base import CredField, register_publisher
from .social import _AccountPublisher, _http_post_form


@register_publisher
class LinkedInOAuthPublisher(_AccountPublisher):
    """LinkedIn publisher with OAuth + ugcPosts."""

    key = "linkedin"
    label = _("LinkedIn")
    description = _("Post to a LinkedIn personal profile with OAuth 2.0. Tokens last ~60 days.")
    icon = "send"
    char_limit = 3000

    oauth_supported = True
    oauth_scopes = ["openid", "profile", "email", "w_member_social"]
    credential_fields: list[CredField] = []

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
    POST_URL = "https://api.linkedin.com/v2/ugcPosts"

    def oauth_authorize_url(self, redirect_uri: str, state: str, pkce_verifier: str) -> str:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['linkedin']['client_id'] is not configured")
        client_id, _ = creds
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.oauth_scopes),
            "state": state,
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    def oauth_exchange(self, code: str, redirect_uri: str, pkce_verifier: str) -> dict:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['linkedin'] is not configured")
        client_id, client_secret = creds

        token_resp = _http_post_form(
            self.TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={},
        )
        access_token = token_resp.get("access_token")
        if not access_token:
            raise RuntimeError(f"LinkedIn token exchange returned no access_token: {token_resp}")

        # Look up the user (the 'sub' is the URN ID we need to author posts).
        req = urllib.request.Request(
            self.USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            me = json.loads(resp.read().decode("utf-8"))

        sub = me.get("sub", "")
        return {
            "credentials": {
                "access_token": access_token,
                "expires_in": token_resp.get("expires_in", 0),
                "person_urn": f"urn:li:person:{sub}" if sub else "",
            },
            "handle": me.get("email") or me.get("name", ""),
            "display_name": me.get("name") or me.get("email") or "",
        }

    def _publish_one(self, job, account) -> None:
        creds = account.get_credentials()
        token = creds.get("access_token")
        person_urn = creds.get("person_urn")
        if not token or not person_urn:
            raise RuntimeError("LinkedIn account is missing access_token or person_urn")

        text = job.body_text or self.default_copy(job)
        body = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                },
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        }
        req = urllib.request.Request(
            self.POST_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()  # ignore body; presence of 201 is enough

    def test_connection(self, account) -> tuple[bool, str]:
        creds = account.get_credentials()
        token = creds.get("access_token")
        if not token:
            return False, "Missing access_token. Reconnect the account."
        try:
            req = urllib.request.Request(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                me = json.loads(resp.read().decode("utf-8"))
            return True, f"Authenticated as {me.get('name') or me.get('email') or '?'}"
        except Exception as e:  # noqa: BLE001
            return False, f"LinkedIn verify failed: {e}"
