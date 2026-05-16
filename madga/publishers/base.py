"""Publisher base class + registry."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madga.models import BroadcastJob


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
    ``publish(job)``. Optionally override ``is_configured()`` to gate
    visibility in the studio drawer when credentials are missing.
    """

    key: str = ""
    label: str = ""
    description: str = ""
    icon: str = ""  # studio icon name from madga_studio_tags

    def is_configured(self) -> bool:
        """Return True if this publisher can actually run (creds present)."""
        return True

    def estimate_targets(self, job: "BroadcastJob") -> int:
        """Return how many recipients ``publish(job)`` would attempt.

        Used by the studio drawer for the recipient count preview.
        """
        return 0

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


def all_publishers(only_configured: bool = False) -> list[Publisher]:
    """Return all registered publishers. Sorted by label for stable UI."""
    items = list(_REGISTRY.values())
    if only_configured:
        items = [p for p in items if p.is_configured()]
    items.sort(key=lambda p: p.label or p.key)
    return items
