"""Seed a default Site, demo content, and the admin SiteUser."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from madga.models import Category, Page, Post, Site, SiteUser, Tag


def _demo_body(title: str) -> dict:
    return {
        "blocks": [
            {"type": "header", "data": {"text": title, "level": 2}},
            {
                "type": "paragraph",
                "data": {
                    "text": (
                        "MADGA es un CMS headless-ready para Django. Este post de ejemplo "
                        "fue creado con <code>madga_seed</code> para verificar que el "
                        "renderer y la API funcionan."
                    )
                },
            },
            {
                "type": "list",
                "data": {
                    "style": "unordered",
                    "items": ["Editor.js wired", "Headless API", "Studio backoffice"],
                },
            },
            {
                "type": "quote",
                "data": {
                    "text": "Make Django Great Again.",
                    "caption": "MADGA",
                },
            },
            {"type": "delimiter", "data": {}},
            {
                "type": "code",
                "data": {"code": "from madga.models import Post\nPost.objects.all()"},
            },
        ]
    }


class Command(BaseCommand):
    help = "Seed a default Site + demo content."

    def handle(self, *args, **options):
        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).first()

        site, created = Site.objects.get_or_create(
            domain="localhost",
            defaults={
                "name": "MADGA Demo",
                "description": "Sitio de demo para probar MADGA.",
                "meta_title": "MADGA Demo",
                "meta_description": "Demo de MADGA — CMS headless para Django.",
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Found'} site: {site.name}"
        ))
        self.stdout.write(f"  API key: {site.api_key}")

        if admin:
            SiteUser.objects.get_or_create(
                site=site, user=admin, defaults={"role": SiteUser.ROLE_OWNER}
            )

        cat, _ = Category.objects.get_or_create(
            site=site, slug="general", defaults={"name": "General", "color": "#6C63FF"}
        )
        tag, _ = Tag.objects.get_or_create(
            site=site, slug="demo", defaults={"name": "demo"}
        )

        for title in ("Hola desde MADGA", "Segundo post de ejemplo"):
            post, post_created = Post.objects.get_or_create(
                site=site,
                title=title,
                defaults={
                    "excerpt": "Post generado por madga_seed para validar la API.",
                    "body": _demo_body(title),
                    "status": Post.STATUS_PUBLISHED,
                    "author": admin,
                    "category": cat,
                    "published_at": timezone.now(),
                },
            )
            if post_created:
                post.tags.add(tag)
            self.stdout.write(
                f"  {'+' if post_created else '·'} post: {post.slug}"
            )

        page, page_created = Page.objects.get_or_create(
            site=site,
            slug="about",
            defaults={
                "title": "About",
                "body": _demo_body("Acerca de MADGA"),
                "status": Post.STATUS_PUBLISHED,
            },
        )
        self.stdout.write(
            f"  {'+' if page_created else '·'} page: /{page.slug}"
        )

        self.stdout.write(self.style.SUCCESS("Done."))
