"""Publishers for the major social channels.

Mastodon and Bluesky ship with **real** ``publish()`` implementations
in 0.3.5 — both authenticate with a simple token (no OAuth dance) so
they're production-ready as soon as the user pastes credentials into
the Channels page.

X (Twitter), LinkedIn, and Instagram remain stubs in 0.3.5 because
their auth flows are OAuth 2.0 with platform-specific app review +
redirect URIs; that work lands in 0.3.6.

For each stub: a developer pastes a token, the channel shows as
Active, the studio composer renders per-channel copy + counters, and
"Send broadcast" creates a BroadcastJob row that records a clear
"not implemented yet" failure so the audit trail is intact.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from django.utils.translation import gettext_lazy as _

from .base import CredField, Publisher, PublishResult, register_publisher


logger = logging.getLogger(__name__)


def _http_post_json(url: str, payload: dict, headers: dict, timeout: int = 15) -> dict:
    """Tiny POST-JSON helper. Returns parsed JSON body on 2xx, raises on error."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _http_post_form(url: str, form: dict, headers: dict, timeout: int = 15) -> dict:
    """POST application/x-www-form-urlencoded."""
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


class _AccountPublisher(Publisher):
    """Common skeleton for account-driven channel publishers.

    Subclasses override ``_publish_one(job, account)`` to perform the
    real API call for a single connected account; this base class
    handles fan-out across every active ``PublisherAccount`` for the
    job's Site and aggregates the per-account results.
    """

    multi_account = True

    def estimate_targets(self, job) -> int:
        from madga.models import PublisherAccount
        if not getattr(job, "site", None):
            return 0
        return PublisherAccount.objects.filter(
            site=job.site, publisher_key=self.key, is_active=True,
        ).count() or 1

    def publish(self, job) -> PublishResult:
        from madga.models import PublisherAccount

        result = PublishResult()
        accounts = list(PublisherAccount.objects.filter(
            site=job.site, publisher_key=self.key, is_active=True,
        ))
        if not accounts:
            return PublishResult(
                sent=0, failed=1,
                errors=[{"target": self.key, "msg": f"No active {self.label} account connected."}],
            )

        for account in accounts:
            try:
                self._publish_one(job, account)
                account.record_use()
                result.sent += 1
            except NotImplementedError as e:
                account.record_error(str(e))
                result.failed += 1
                result.errors.append({"target": account.handle or self.key, "msg": str(e)})
            except Exception as e:  # noqa: BLE001
                logger.warning("publisher %s failed for %s: %s", self.key, account.handle, e)
                account.record_error(str(e))
                result.failed += 1
                result.errors.append({"target": account.handle or self.key, "msg": str(e)})
        return result

    def _publish_one(self, job, account) -> None:
        """Override to perform the real API call. Raise on failure."""
        raise NotImplementedError(
            f"{self.label} publishing is not implemented yet. "
            f"Real OAuth + API integration lands in 0.3.6."
        )


# Back-compat alias for anyone importing the old name (host projects).
_AccountStubPublisher = _AccountPublisher


# TwitterPublisher moved to madga/publishers/twitter.py with real OAuth.


@register_publisher
class MastodonPublisher(_AccountPublisher):
    """Mastodon publisher — POSTs a status to /api/v1/statuses.

    Real implementation: takes the configured instance URL + an
    access token (generated from the user's Mastodon account under
    Preferences → Development → New application with ``write:statuses``
    scope) and POSTs the text. No OAuth dance required for this flow.
    """

    key = "mastodon"
    label = _("Mastodon")
    description = _("Post to a Mastodon instance with an account access token.")
    icon = "send"
    char_limit = 500
    credential_fields = [
        CredField(
            "instance_url", _("Instance URL"),
            placeholder="https://hachyderm.io",
            help_text=_("The base URL of the Mastodon server you're posting to."),
        ),
        CredField("access_token", _("Access Token"), secret=True),
    ]

    def _publish_one(self, job, account) -> None:
        creds = account.get_credentials()
        instance = (creds.get("instance_url") or "").rstrip("/")
        token = creds.get("access_token")
        if not instance or not token:
            raise RuntimeError("Mastodon account is missing instance_url or access_token")
        text = job.body_text or self.default_copy(job)
        _http_post_form(
            f"{instance}/api/v1/statuses",
            {"status": text, "visibility": "public"},
            {"Authorization": f"Bearer {token}"},
        )

    def test_connection(self, account) -> tuple[bool, str]:
        creds = account.get_credentials()
        instance = (creds.get("instance_url") or "").rstrip("/")
        token = creds.get("access_token")
        if not instance or not token:
            return False, "Missing instance_url or access_token"
        try:
            req = urllib.request.Request(
                f"{instance}/api/v1/accounts/verify_credentials",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return True, f"Verified as @{data.get('username', '?')} on {instance}"
        except Exception as e:  # noqa: BLE001
            return False, f"Mastodon verify failed: {e}"


@register_publisher
class BlueskyPublisher(_AccountPublisher):
    """Bluesky publisher — AT Protocol ``createSession`` + ``createRecord``.

    Two API calls per post:
    1. ``com.atproto.server.createSession`` with handle + app_password
       → returns an ``accessJwt`` (short-lived).
    2. ``com.atproto.repo.createRecord`` with the JWT + a Post record.
    No OAuth dance; the app password the user generates under their
    Bluesky settings is the only secret we store.
    """

    key = "bluesky"
    label = _("Bluesky")
    description = _("Post to a Bluesky account using its AT Protocol app password.")
    icon = "send"
    char_limit = 300
    credential_fields = [
        CredField("handle", _("Handle"), placeholder="you.bsky.social"),
        CredField(
            "app_password", _("App password"), secret=True,
            help_text=_("Generate an app-specific password under Bluesky → Settings → App Passwords."),
        ),
    ]

    PDS = "https://bsky.social"  # public personal data server

    def _create_session(self, handle: str, password: str) -> dict:
        return _http_post_json(
            f"{self.PDS}/xrpc/com.atproto.server.createSession",
            {"identifier": handle, "password": password},
            headers={},
        )

    def _publish_one(self, job, account) -> None:
        from django.utils import timezone

        creds = account.get_credentials()
        handle = creds.get("handle")
        password = creds.get("app_password")
        if not handle or not password:
            raise RuntimeError("Bluesky account is missing handle or app_password")

        session = self._create_session(handle, password)
        access_jwt = session.get("accessJwt")
        did = session.get("did")
        if not access_jwt or not did:
            raise RuntimeError("Bluesky createSession returned no accessJwt/did")

        text = job.body_text or self.default_copy(job)
        record = {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": timezone.now().isoformat().replace("+00:00", "Z"),
            },
        }
        _http_post_json(
            f"{self.PDS}/xrpc/com.atproto.repo.createRecord",
            record,
            {"Authorization": f"Bearer {access_jwt}"},
        )

    def test_connection(self, account) -> tuple[bool, str]:
        creds = account.get_credentials()
        handle = creds.get("handle")
        password = creds.get("app_password")
        if not handle or not password:
            return False, "Missing handle or app_password"
        try:
            session = self._create_session(handle, password)
            did = session.get("did")
            return True, f"Authenticated as {handle} (did:{(did or '')[:24]}…)"
        except Exception as e:  # noqa: BLE001
            return False, f"Bluesky auth failed: {e}"


# LinkedInPublisher moved to madga/publishers/linkedin.py with real OAuth.
# InstagramPublisher moved to madga/publishers/instagram.py with real OAuth + Graph API.
