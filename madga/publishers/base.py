"""Publisher base class + registry."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madga.models import BroadcastJob, PublisherAccount, Site


@dataclass
class CredField:
    """Declarative credential field a Publisher requires.

    Drives the Channels page "Connect" form: each entry renders a
    labelled input (text by default, password when ``secret=True``).
    Used only for publishers that don't have a real OAuth flow yet —
    a developer pastes the token they got from the platform's
    developer console.
    """

    name: str
    label: str
    secret: bool = False
    placeholder: str = ""
    help_text: str = ""


@dataclass
class PublishResult:
    """Return value of ``Publisher.publish``.

    The worker collects this and writes the counts onto the BroadcastJob.
    Each error in ``errors`` is a dict like ``{"target": "<id>", "msg": "..."}``.
    """

    sent: int = 0
    failed: int = 0
    errors: list = field(default_factory=list)


class Publisher:
    """A destination MADGA can broadcast to.

    Subclass + register via ``@register_publisher`` to wire a new one.
    Subclasses must declare ``key``, ``label``, and override
    ``publish(job)``.

    Two flavors of publisher coexist:

    1. **Settings-driven** (legacy / dev): ``is_configured()`` returns
       True iff some env var is set. One global account per
       deployment. The built-in ``email_subscribers`` works this way.
    2. **Account-driven** (multi-tenant): ``credential_fields`` is
       non-empty, ``is_configured(site)`` returns True iff there's an
       active ``PublisherAccount`` for that Site. Each Site gets its
       own credentials, paused independently. This is the SaaS path
       (LinkedIn, X, Mastodon, Bluesky, etc.).
    """

    key: str = ""
    label: str = ""
    description: str = ""
    icon: str = ""  # studio icon name from madga_studio_tags

    # If non-empty, the publisher is treated as account-driven: the
    # Channels page renders a Connect form using these fields, and a
    # PublisherAccount must exist for a Site before is_configured(site)
    # returns True.
    credential_fields: list[CredField] = []

    # Character limit per post (for the per-channel composer's counter).
    # None = no client-side limit.
    char_limit: int | None = None

    # Whether ``publish(job)`` accepts a per-account split or always
    # publishes globally. Account-driven publishers default to True.
    multi_account: bool = False

    def is_configured(self, site: "Site | None" = None) -> bool:
        """Return True if this publisher can actually run.

        Account-driven publishers require at least one active
        ``PublisherAccount`` for the given Site. Settings-driven
        publishers ignore the site argument and check globals.
        """
        if self.credential_fields:
            if site is None:
                return False
            from madga.models import PublisherAccount
            return PublisherAccount.objects.filter(
                site=site, publisher_key=self.key, is_active=True,
            ).exists()
        return True

    def estimate_targets(self, job: "BroadcastJob") -> int:
        """Return how many recipients ``publish(job)`` would attempt.

        Used by the studio drawer for the recipient count preview.
        """
        return 0

    def default_copy(self, job: "BroadcastJob") -> str:
        """Return the auto-generated text for this channel.

        Override to tweak per platform (e.g., X may want hashtags,
        LinkedIn longer body). Default: subject + url, truncated to
        ``char_limit``.
        """
        body = (job.subject or "").strip()
        url = (job.related_url or "").strip()
        text = f"{body}\n\n{url}".strip() if url else body
        if self.char_limit and len(text) > self.char_limit:
            # Keep room for the URL on the last line if present.
            ellipsis_sep = "…\n\n"  # 3 chars: "…" + "\n\n"
            if url and len(url) + len(ellipsis_sep) < self.char_limit:
                budget = self.char_limit - len(url) - len(ellipsis_sep)
                text = body[:budget].rstrip() + ellipsis_sep + url
            else:
                text = text[: self.char_limit - 1].rstrip() + "…"
        return text

    def publish(self, job: "BroadcastJob") -> PublishResult:
        """Actually send the broadcast. Must be implemented by subclasses."""
        raise NotImplementedError


_REGISTRY: dict[str, Publisher] = {}


def register_publisher(cls):
    """Decorator: register a Publisher subclass by its ``key``."""
    if not getattr(cls, "key", None):
        raise ValueError(f"{cls.__name__} must declare a non-empty `key` attribute.")
    instance = cls()
    _REGISTRY[cls.key] = instance
    return cls


def get_publisher(key: str) -> Publisher | None:
    return _REGISTRY.get(key)


def all_publishers(
    only_configured: bool = False,
    site: "Site | None" = None,
) -> list[Publisher]:
    """Return all registered publishers. Sorted by label for stable UI.

    Pass ``site`` together with ``only_configured=True`` to filter by
    *that Site's* connected accounts (the account-driven SaaS path).
    Otherwise account-driven publishers will be filtered out as
    "unconfigured" even when accounts exist for some other site.
    """
    items = list(_REGISTRY.values())
    if only_configured:
        items = [p for p in items if p.is_configured(site)]
    items.sort(key=lambda p: str(p.label or p.key))
    return items
