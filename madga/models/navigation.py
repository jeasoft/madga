"""Navigation: site-level nav menu items (v0.2)."""

from django.db import models

from .base import TimestampMixin


class NavItem(TimestampMixin, models.Model):
    """A single item in a Site's navigation menu.

    Items can nest via ``parent`` (one level is enough for v0.2 but the model
    permits arbitrary depth). Ordering is purely numeric — the Studio editor
    offers integer inputs for ``sort_order`` instead of drag-and-drop.
    """

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="nav_items"
    )
    label = models.CharField(max_length=100)
    url = models.CharField(
        max_length=500,
        help_text="Relative path (e.g. /blog/) or absolute URL.",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["site", "parent", "sort_order"])]

    def __str__(self) -> str:
        return self.label
