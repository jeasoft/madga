"""Build MADGA Tailwind CSS bundles using the standalone tailwindcss binary."""

import shutil
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


TARGETS = {
    "blog": ("blog/tailwind.input.css", "blog/tailwind.css"),
    "studio": ("studio/studio.tailwind.input.css", "studio/studio.tailwind.css"),
}


class Command(BaseCommand):
    help = "Build (or watch) MADGA Tailwind bundles via the standalone binary."

    def add_arguments(self, parser):
        parser.add_argument(
            "target",
            nargs="?",
            choices=list(TARGETS.keys()) + ["all"],
            default="all",
            help="Which bundle to build (blog, studio, or all).",
        )
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--no-minify", action="store_true")

    def handle(self, *args, **opts):
        binary = shutil.which("tailwindcss")
        if not binary:
            self.stderr.write(self.style.ERROR(
                "`tailwindcss` not found in PATH. Install the standalone binary: "
                "https://tailwindcss.com/blog/standalone-cli"
            ))
            sys.exit(1)

        app_root = Path(__file__).resolve().parents[2]
        targets = list(TARGETS) if opts["target"] == "all" else [opts["target"]]

        if opts["watch"] and len(targets) > 1:
            self.stderr.write(self.style.WARNING(
                "--watch only watches the LAST target. Run separate processes "
                "if you need to watch multiple bundles."
            ))

        for name in targets:
            inp, out = TARGETS[name]
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
