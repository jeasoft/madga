"""Taxonomy: Category and Tag."""

from django.db import models


class Category(models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    color = models.CharField(max_length=7, default="#6C63FF")
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [["site", "slug"]]
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        unique_together = [["site", "slug"]]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
