"""Serve the standalone CMS prototype that lives in `prototype/`.

The prototype is an Alpine.js + Tailwind single-page mockup that the team
uses as the visual reference for the Studio backoffice. It is NOT part of
the Django app (no template inheritance, hardcoded data) and is mounted
under `/prototype/` purely so it can be reviewed in the browser alongside
the live Studio.
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404

PROTOTYPE_DIR: Path = settings.BASE_DIR / "prototype"

# Whitelist the assets we are willing to serve to avoid arbitrary file reads.
_ASSETS = {
    "styles.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}


def _file_response(name: str, content_type: str) -> FileResponse:
    path = PROTOTYPE_DIR / name
    if not path.is_file():
        raise Http404(f"prototype asset missing: {name}")
    return FileResponse(path.open("rb"), content_type=content_type)


def prototype_index(request):
    """Render the prototype HTML page."""
    return _file_response("prototype.html", "text/html; charset=utf-8")


def prototype_asset(request, name: str):
    """Serve a whitelisted prototype asset (styles.css, app.js)."""
    content_type = _ASSETS.get(name)
    if content_type is None:
        raise Http404(f"prototype asset not allowed: {name}")
    return _file_response(name, content_type)
