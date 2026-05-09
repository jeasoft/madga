"""Signals: auto-slug, body_html caching."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from slugify import slugify

from madga.models import Page, Post
from madga.renderer import render_blocks


def _unique_slug(model, base: str, instance) -> str:
    candidate = base or "post"
    n = 1
    qs = model.objects.exclude(pk=instance.pk) if instance.pk else model.objects.all()
    while qs.filter(slug=candidate).exists():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


@receiver(pre_save, sender=Post)
def post_pre_save(sender, instance: Post, **kwargs):
    if not instance.slug:
        instance.slug = _unique_slug(Post, slugify(instance.title)[:480], instance)
    instance.body_html = render_blocks(instance.body)


@receiver(pre_save, sender=Page)
def page_pre_save(sender, instance: Page, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)[:480]
    instance.body_html = render_blocks(instance.body)
