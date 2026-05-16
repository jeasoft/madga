"""Stub publishers for the major social channels.

These ship with MADGA so the Channels UI has something to render on
day one. They cover credential storage + an ``is_configured()`` check
+ ``default_copy()`` tuned for each platform's character limits. The
actual ``publish()`` call is a stub that records ``last_error`` —
host projects (or future MADGA versions) replace it with the real
API call.

Real OAuth flows + production-grade publishing land in 0.3.5. Until
then a developer can:

  - Paste an API token / access token into the Channels Connect form
  - See the channel appear as Active
  - The studio composer shows per-channel copy + character count
  - Hitting "Send broadcast" creates the BroadcastJob row (so the
    audit trail is intact) and marks it failed with a clear message

This lets aplica.do flesh out the UX without waiting on the OAuth
plumbing.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from .base import CredField, Publisher, PublishResult, register_publisher


class _AccountStubPublisher(Publisher):
    """Common skeleton for the social channel stubs."""

    multi_account = True

    def estimate_targets(self, job) -> int:
        # One job-per-account; the "target" here is each connected
        # account that's active for this Site.
        from madga.models import PublisherAccount
        if not getattr(job, "site", None):
            return 0
        return PublisherAccount.objects.filter(
            site=job.site, publisher_key=self.key, is_active=True,
        ).count() or 1

    def publish(self, job) -> PublishResult:
        # Real implementation lives in 0.3.5. For now: mark the job
        # failed with an actionable message so the audit log makes it
        # obvious what's missing.
        return PublishResult(
            sent=0, failed=job.targets_count or 1,
            errors=[{
                "target": self.key,
                "msg": (
                    f"{self.label} publishing is not implemented yet. "
                    f"Use the Channels page to connect an account; the "
                    f"real API call lands in 0.3.5 or via a host-project "
                    f"override."
                ),
            }],
        )


@register_publisher
class TwitterPublisher(_AccountStubPublisher):
    key = "twitter"
    label = _("X (Twitter)")
    description = _("Post to an X account using its API v2 credentials.")
    icon = "send"
    char_limit = 280
    credential_fields = [
        CredField("api_key", _("API Key"), placeholder="…"),
        CredField("api_secret", _("API Key Secret"), secret=True),
        CredField("access_token", _("Access Token"), secret=True),
        CredField("access_secret", _("Access Token Secret"), secret=True),
    ]


@register_publisher
class MastodonPublisher(_AccountStubPublisher):
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


@register_publisher
class BlueskyPublisher(_AccountStubPublisher):
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


@register_publisher
class LinkedInPublisher(_AccountStubPublisher):
    key = "linkedin"
    label = _("LinkedIn")
    description = _("Post to a LinkedIn personal profile or company page.")
    icon = "send"
    char_limit = 3000
    credential_fields = [
        CredField("access_token", _("Access Token"), secret=True),
        CredField(
            "owner_urn", _("Owner URN"),
            placeholder="urn:li:person:xxxxx or urn:li:organization:xxxxx",
            help_text=_("Whose page to post on. Find it in your LinkedIn developer console."),
        ),
    ]
