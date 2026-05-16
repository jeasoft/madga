"""MADGA CLI: a single command that dispatches to subcommands.

    python manage.py madga --help
    python manage.py madga create-site --name "My Blog" --domain blog.com
    python manage.py madga seed-demo
    python manage.py madga build-css [--watch]
    python manage.py madga version
    python manage.py madga blocks   # list registered block types
"""

from __future__ import annotations

import getpass
import shutil
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import timezone


TAILWIND_TARGETS = {
    "blog": ("blog/tailwind.input.css", "blog/tailwind.css"),
    "studio": ("studio/studio.tailwind.input.css", "studio/studio.tailwind.css"),
}


class Command(BaseCommand):
    help = (
        "MADGA CLI. Subcommands: create-site, seed-demo, build-css, blocks, version. "
        "Run `python manage.py madga <subcommand> --help` for details."
    )

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="cmd", required=True, metavar="subcommand")

        # create-site -------------------------------------------------------
        c = sub.add_parser(
            "create-site",
            help="Create or update a Site row + owner SiteUser.",
        )
        c.add_argument("--name")
        c.add_argument("--domain")
        c.add_argument("--theme", default="default")
        c.add_argument("--accent-color", default="#6C63FF")
        c.add_argument("--owner-username")
        c.add_argument("--owner-email")
        c.add_argument("--owner-password")
        c.add_argument(
            "--non-interactive", action="store_true",
            help="Fail instead of prompting for missing fields.",
        )

        # seed-demo ---------------------------------------------------------
        s = sub.add_parser(
            "seed-demo",
            help="Seed demo content (Site, posts, page, category, tag) for trying things out.",
        )
        s.add_argument("--domain", default="localhost")

        # build-css ---------------------------------------------------------
        b = sub.add_parser(
            "build-css",
            help="Build MADGA Tailwind bundles via the standalone binary.",
        )
        b.add_argument(
            "target", nargs="?",
            choices=list(TAILWIND_TARGETS.keys()) + ["all"], default="all",
        )
        b.add_argument("--watch", action="store_true")
        b.add_argument("--no-minify", action="store_true")

        # blocks ------------------------------------------------------------
        sub.add_parser("blocks", help="List registered BlockTypes.")

        # version -----------------------------------------------------------
        sub.add_parser("version", help="Print MADGA version.")

        # backfill-profiles -------------------------------------------------
        bp = sub.add_parser(
            "backfill-profiles",
            help="Re-fire user_post_signup for every User (useful after wiring a new profile receiver).",
        )
        bp.add_argument("--kind", default="", help="Pass as `kind` to the signal.")

        # broadcast-worker --------------------------------------------------
        bw = sub.add_parser(
            "broadcast-worker",
            help="Drain pending BroadcastJobs (one-shot by default; --loop to keep running).",
        )
        bw.add_argument("--loop", action="store_true",
                        help="Keep running and poll every --interval seconds.")
        bw.add_argument("--interval", type=int, default=30,
                        help="Poll interval in seconds when --loop is set (default 30).")
        bw.add_argument("--limit", type=int, default=50,
                        help="Max jobs to process per pass (default 50).")

        # publishers --------------------------------------------------------
        sub.add_parser("publishers", help="List registered Publishers.")

    def handle(self, *args, **opts):
        cmd = opts.pop("cmd")
        method = getattr(self, f"_cmd_{cmd.replace('-', '_')}", None)
        if method is None:
            raise CommandError(f"Unknown subcommand: {cmd!r}")
        method(opts)

    # ---- subcommand handlers -----------------------------------------------

    def _prompt(self, label, default=None, *, secret=False, non_interactive=False):
        if non_interactive:
            raise CommandError(
                f"Missing --{label.replace(' ', '-').lower()} in non-interactive mode."
            )
        prompt = f"{label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = (getpass.getpass(prompt) if secret else input(prompt)).strip()
        return value or default or ""

    def _cmd_create_site(self, opts):
        from madga.models import Site, SiteUser

        ni = opts.get("non_interactive", False)
        name = opts.get("name") or self._prompt(
            "Site name", default="My Site", non_interactive=ni
        )
        domain = opts.get("domain") or self._prompt(
            "Domain", default="localhost", non_interactive=ni
        )
        theme = opts.get("theme") or "default"
        accent = opts.get("accent_color") or "#6C63FF"

        owner_username = opts.get("owner_username") or self._prompt(
            "Owner username (existing or new)", default="admin", non_interactive=ni
        )
        owner_email = opts.get("owner_email") or self._prompt(
            "Owner email", default=f"{owner_username}@{domain}", non_interactive=ni
        )

        site, created = Site.objects.update_or_create(
            domain=domain,
            defaults={"name": name, "theme": theme, "accent_color": accent},
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} Site #{site.pk}: {name} ({domain})"))

        User = get_user_model()
        user = User.objects.filter(username=owner_username).first()
        if user is None:
            owner_password = opts.get("owner_password") or self._prompt(
                "Owner password (won't echo)", secret=True, non_interactive=ni
            )
            if not owner_password:
                raise CommandError("Owner password required when creating a new user.")
            user = User.objects.create_user(
                username=owner_username, email=owner_email, password=owner_password,
            )
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser {owner_username}"))
        else:
            self.stdout.write(f"Reusing existing user {owner_username}")

        SiteUser.objects.get_or_create(
            site=site, user=user, defaults={"role": SiteUser.ROLE_OWNER},
        )
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Next: python manage.py runserver"))
        self.stdout.write(self.style.NOTICE(f"      open http://localhost:8000/studio/  (login: {owner_username})"))

    def _cmd_seed_demo(self, opts):
        from madga.models import Category, Page, Post, Site, SiteUser, Tag

        domain = opts.get("domain", "localhost")
        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).first()

        site, created = Site.objects.get_or_create(
            domain=domain,
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

        body = {
            "blocks": [
                {"type": "header", "data": {"text": "Hola desde MADGA", "level": 2}},
                {"type": "paragraph", "data": {"text": "Demo seed para validar el render."}},
                {"type": "list", "data": {
                    "style": "unordered",
                    "items": ["Editor.js", "Headless API", "Studio"],
                }},
            ]
        }
        for title in ("Hola desde MADGA", "Segundo post de ejemplo"):
            post, was_new = Post.objects.get_or_create(
                site=site, title=title,
                defaults={
                    "excerpt": "Post generado por madga seed-demo.",
                    "body": body,
                    "status": Post.STATUS_PUBLISHED,
                    "author": admin,
                    "category": cat,
                    "published_at": timezone.now(),
                },
            )
            if was_new:
                post.tags.add(tag)
            self.stdout.write(f"  {'+' if was_new else '·'} post: {post.slug}")

        page, was_new = Page.objects.get_or_create(
            site=site, slug="about",
            defaults={"title": "About", "body": body, "status": Post.STATUS_PUBLISHED},
        )
        self.stdout.write(f"  {'+' if was_new else '·'} page: /{page.slug}")
        self.stdout.write(self.style.SUCCESS("Done."))

    def _cmd_build_css(self, opts):
        binary = shutil.which("tailwindcss")
        if not binary:
            self.stderr.write(self.style.ERROR(
                "`tailwindcss` not found in PATH. Install the standalone binary: "
                "https://tailwindcss.com/blog/standalone-cli"
            ))
            sys.exit(1)

        # Path to the installed madga module's static dir.
        import madga
        app_root = Path(madga.__file__).resolve().parent
        targets = list(TAILWIND_TARGETS) if opts["target"] == "all" else [opts["target"]]

        if opts["watch"] and len(targets) > 1:
            self.stderr.write(self.style.WARNING(
                "--watch only watches the LAST target. Run separate processes "
                "to watch multiple bundles."
            ))

        for name in targets:
            inp, out = TAILWIND_TARGETS[name]
            cmd = [
                binary,
                "-i", str(app_root / "static" / "madga" / inp),
                "-o", str(app_root / "static" / "madga" / out),
            ]
            if not opts["no_minify"]:
                cmd.append("--minify")
            if opts["watch"] and name == targets[-1]:
                cmd.append("--watch")
            self.stdout.write(self.style.NOTICE(f"[{name}] {' '.join(cmd)}"))
            subprocess.run(cmd, check=False)

    def _cmd_blocks(self, opts):
        from madga.blocks import all_block_types

        types = all_block_types()
        if not types:
            self.stdout.write("No block types registered.")
            return
        self.stdout.write(f"{len(types)} block type(s) registered:\n")
        for bt in types:
            self.stdout.write(f"  {self.style.SUCCESS(bt.key):40s}  {bt.label}")
            if bt.description:
                self.stdout.write(f"    {bt.description}")
            self.stdout.write(f"    template: {bt.template}")
            field_summary = ", ".join(f.name for f in bt.fields) or "—"
            self.stdout.write(f"    fields:   {field_summary}")
            self.stdout.write("")

    def _cmd_version(self, opts):
        import madga
        self.stdout.write(f"MADGA {madga.__version__}")

    def _cmd_backfill_profiles(self, opts):
        from madga.signals import user_post_signup

        User = get_user_model()
        kind = opts.get("kind", "")
        n = 0
        for u in User.objects.all().iterator():
            user_post_signup.send(sender=User, user=u, request=None, kind=kind)
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f"Fired user_post_signup for {n} user(s) (kind={kind!r})."
        ))

    def _cmd_publishers(self, opts):
        from madga.publishers import all_publishers

        items = all_publishers()
        if not items:
            self.stdout.write("No publishers registered.")
            return
        self.stdout.write(f"{len(items)} publisher(s) registered:\n")
        for p in items:
            ok = "✓" if p.is_configured() else "·"
            label = str(p.label) if p.label else p.key
            self.stdout.write(f"  {ok} {self.style.SUCCESS(p.key):28s}  {label}")
            if p.description:
                self.stdout.write(f"      {p.description}")

    def _cmd_broadcast_worker(self, opts):
        import time
        from django.utils import timezone
        from madga.models import BroadcastJob
        from madga.studio.views.broadcasts import _worker_run

        def pass_once() -> int:
            now = timezone.now()
            qs = BroadcastJob.objects.filter(
                status=BroadcastJob.STATUS_PENDING,
            ).filter(
                models.Q(scheduled_at__isnull=True) | models.Q(scheduled_at__lte=now)
            ).order_by("created_at")[: opts["limit"]]
            n = 0
            for job in qs:
                self.stdout.write(f"→ {job.publisher_key} job {job.pk}…")
                _worker_run(job)
                self.stdout.write(self.style.SUCCESS(
                    f"  done: sent={job.sent_count} failed={job.failed_count}"
                ))
                n += 1
            return n

        if opts["loop"]:
            self.stdout.write(self.style.NOTICE(
                f"broadcast-worker loop (interval={opts['interval']}s). Ctrl-C to stop."
            ))
            while True:
                pass_once()
                time.sleep(opts["interval"])
        else:
            n = pass_once()
            self.stdout.write(self.style.SUCCESS(f"Processed {n} job(s)."))
