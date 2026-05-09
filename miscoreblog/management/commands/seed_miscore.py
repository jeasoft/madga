"""Seed the miscoreblog DB with the miscore.app Site row.

    python manage.py seed_miscore --settings=miscoreblog.settings

Idempotent — safe to run repeatedly. Updates existing Site if domain
matches. Creates an admin user (admin/admin) if none exists.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from madga.models import Site, SiteUser


class Command(BaseCommand):
    help = "Seed the miscoreblog DB: create or update the miscore.app Site."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ga", default="", help="Google Analytics 4 measurement id (G-XXXXXXX)."
        )
        parser.add_argument(
            "--pixel", default="", help="Meta Pixel id."
        )

    def handle(self, *args, **opts):
        site, created = Site.objects.update_or_create(
            domain="miscore.app",
            defaults={
                "name": "miscore.app",
                "description": "Construye tu reputación financiera desde WhatsApp.",
                "accent_color": "#E67522",
                "heading_font": "Helvena",
                "body_font": "Helvena",
                "color_scheme": "light",
                "theme": "miscore",
                "meta_title": "miscore.app — Construye tu reputación financiera desde WhatsApp",
                "meta_description": "Construye tu reputación financiera desde WhatsApp.",
                "google_analytics_id": opts["ga"] or "",
                "facebook_pixel_id": opts["pixel"] or "",
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} Site #{site.pk}: {site.name} ({site.domain})"))

        # Ensure an admin exists. Studio middleware also accepts superusers
        # without a SiteUser, but we add one anyway for clarity.
        User = get_user_model()
        admin, made = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if made:
            admin.set_password("admin")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin/admin)."))
        SiteUser.objects.get_or_create(site=site, user=admin, defaults={"role": "owner"})

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Next steps:"))
        self.stdout.write("  1. Run: python manage.py runserver --settings=miscoreblog.settings 9877")
        self.stdout.write("  2. Open http://localhost:9877/        → miscore landing")
        self.stdout.write("  3. Open http://localhost:9877/privacidad/  → legal page")
        self.stdout.write("  4. Open http://localhost:9877/terminos/    → legal page")
        self.stdout.write("  5. Open http://localhost:9877/studio/      → MADGA studio (admin/admin)")
        self.stdout.write("")
        self.stdout.write("To enable tracking, re-run with:")
        self.stdout.write("  python manage.py seed_miscore --ga G-XXXXXXX --pixel 123456789012345 --settings=miscoreblog.settings")
