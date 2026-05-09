"""Homepage blocks builder (v0.2)."""

from django.db import models

from .base import TimestampMixin


class HomepageBlock(TimestampMixin, models.Model):
    """A composable block on a Site's homepage.

    The ``config`` JSONField is intentionally schemaless — each ``block_type``
    interprets it differently (e.g. a ``hero`` reads ``title``/``subtitle``/
    ``cta_label``/``cta_url``, while ``recent_posts`` reads ``count``).
    """

    BLOCK_HERO = "hero"
    BLOCK_RECENT_POSTS = "recent_posts"
    BLOCK_FEATURED_POST = "featured_post"
    BLOCK_NEWSLETTER = "newsletter"
    BLOCK_TEXT = "text"
    BLOCK_CTA = "cta"
    BLOCK_TYPE_CHOICES = [
        (BLOCK_HERO, "Hero"),
        (BLOCK_RECENT_POSTS, "Recent posts"),
        (BLOCK_FEATURED_POST, "Featured post"),
        (BLOCK_NEWSLETTER, "Newsletter"),
        (BLOCK_TEXT, "Text"),
        (BLOCK_CTA, "Call to action"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="homepage_blocks"
    )
    block_type = models.CharField(max_length=30, choices=BLOCK_TYPE_CHOICES)
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["site", "sort_order"])]

    def __str__(self) -> str:
        return f"{self.get_block_type_display()} (#{self.sort_order})"
