"""Navigation: site-level nav menu items (v0.2)."""

from django.db import models

from .base import TimestampMixin


class NavItem(TimestampMixin, models.Model):
    """A single item in a Site's navigation menu.

    Items can nest via ``parent`` (one level is enough but the model permits
    arbitrary depth). ``location`` separates header items from footer
    columns — footer parents are column titles; their children are links.
    """

    LOCATION_HEADER = "header"
    LOCATION_FOOTER = "footer"
    LOCATION_CHOICES = [
        (LOCATION_HEADER, "Header"),
        (LOCATION_FOOTER, "Footer"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="nav_items"
    )
    location = models.CharField(
        max_length=20, choices=LOCATION_CHOICES, default=LOCATION_HEADER,
    )
    label = models.CharField(max_length=100)
    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path (e.g. /blog/), absolute URL, or empty for footer column titles.",
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
        indexes = [models.Index(fields=["site", "location", "parent", "sort_order"])]

    def __str__(self) -> str:
        return self.label
