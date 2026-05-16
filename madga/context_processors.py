"""Template context processors for MADGA."""

from madga.models import MediaFile, Page, Post, Site


def current_site(request):
    """Inject the active Site into all templates.

    Exposes the same Site under two keys:
    - ``site``        — convenient short name used everywhere in MADGA's own templates
    - ``madga_site``  — stable name that survives third-party views (e.g. allauth)
      which overwrite ``site`` with ``django.contrib.sites``' Site in their
      ``get_context_data``. Anywhere we need to be sure we have the MADGA Site
      (template tags, host-project templates) we should reach for ``madga_site``.
    """
    site = getattr(request, "madga_site", None)
    if site is None:
        site = Site.objects.filter(is_active=True).order_by("id").first()
        if site is not None:
            request.madga_site = site
    return {"site": site, "madga_site": site}


def studio_topbar(request):
    """Topbar widgets: recent activity for the notifications panel.

    Cheap query: 5 most recent posts/pages/media for the active site.
    Only enabled inside the studio, where it's actually shown.
    """
    if not request.path.startswith("/studio"):
        return {}
    site = getattr(request, "madga_site", None)
    if site is None:
        return {"recent_activity": []}

    events = []
    posts = (
        Post.objects.alive()
        .filter(site=site)
        .order_by("-updated_at")
        .values("id", "title", "status", "updated_at", "published_at")[:5]
    )
    for p in posts:
        kind = "published" if p["status"] == "published" else "draft"
        label = "Publicado" if kind == "published" else "Borrador"
        events.append(
            {
                "title": p["title"] or "Sin título",
                "kind": kind,
                "label": label,
                "when": p["updated_at"],
                "url": f"/studio/posts/{p['id']}/edit/",
            }
        )
    pages = (
        Page.objects.filter(site=site)
        .order_by("-updated_at")
        .values("id", "title", "updated_at")[:3]
    )
    for pg in pages:
        events.append(
            {
                "title": pg["title"] or "Sin título",
                "kind": "draft",
                "label": "Página",
                "when": pg["updated_at"],
                "url": f"/studio/pages/{pg['id']}/edit/",
            }
        )
    media = (
        MediaFile.objects.filter(site=site)
        .order_by("-created_at")
        .values("filename", "created_at")[:3]
    )
    for m in media:
        events.append(
            {
                "title": m["filename"],
                "kind": "media",
                "label": "Archivo subido",
                "when": m["created_at"],
                "url": "/studio/media/",
            }
        )
    events.sort(key=lambda e: e["when"], reverse=True)
    return {"recent_activity": events[:8]}
