"""Publisher registry: outbound fan-out for broadcasts.

Host projects register their own Publishers in ``apps.ready()``:

    from madga.publishers import Publisher, register_publisher

    @register_publisher
    class LinkedInPublisher(Publisher):
        key = "linkedin"
        label = "LinkedIn"
        description = "Post to the org's LinkedIn page."

        def is_configured(self):
            return bool(getattr(settings, "LINKEDIN_ACCESS_TOKEN", None))

        def publish(self, job):
            ...  # call LinkedIn API, return PublishResult

The studio "Broadcast" drawer lists every registered Publisher whose
``is_configured()`` returns True. The built-in ``email_subscribers``
Publisher uses Django's email backend and ships in this package.
"""

from .base import (
    Publisher,
    PublishResult,
    all_publishers,
    get_publisher,
    register_publisher,
)

# Side-effect: registers the built-in email publisher.
from . import email  # noqa: F401

__all__ = [
    "Publisher",
    "PublishResult",
    "all_publishers",
    "get_publisher",
    "register_publisher",
]
