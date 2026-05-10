"""Content: Post and Page."""

from django.conf import settings
from django.db import models

from .base import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Post(UUIDMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_SCHEDULED = "scheduled"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Borrador"),
        (STATUS_PUBLISHED, "Publicado"),
        (STATUS_SCHEDULED, "Programado"),
        (STATUS_ARCHIVED, "Archivado"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True, blank=True)
    excerpt = models.TextField(blank=True)
    body = models.JSONField(default=dict, blank=True)
    body_html = models.TextField(blank=True)

    featured_image = models.ForeignKey(
        "madga.MediaFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="featured_in_posts",
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="madga_posts",
    )

    category = models.ForeignKey(
        "madga.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    tags = models.ManyToManyField("madga.Tag", blank=True, related_name="posts")

    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    views = models.PositiveIntegerField(default=0)

    # SEO
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(blank=True)
    og_image = models.ForeignKey(
        "madga.MediaFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="og_in_posts",
    )
    focus_keyword = models.CharField(max_length=100, blank=True)
    canonical_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["site", "status", "published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_publicly_visible(self) -> bool:
        """True if this post should appear on the public blog right now."""
        from django.utils import timezone

        if self.is_deleted:
            return False
        if self.status == self.STATUS_PUBLISHED:
            return self.published_at is None or self.published_at <= timezone.now()
        return False


class Page(UUIDMixin, TimestampMixin, models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="pages"
    )
    title = models.CharField(max_length=500)
    slug = models.CharField(max_length=500)
    body = models.JSONField(default=dict, blank=True)
    body_html = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Post.STATUS_CHOICES, default=Post.STATUS_DRAFT
    )
    layout = models.CharField(max_length=50, default="simple")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)

    featured_image = models.ForeignKey(
        "madga.MediaFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="featured_in_pages",
    )

    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(blank=True)
    og_image = models.ForeignKey(
        "madga.MediaFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="og_in_pages",
    )

    class Meta:
        ordering = ["sort_order"]
        unique_together = [["site", "slug"]]

    def __str__(self) -> str:
        return self.title
