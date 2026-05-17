"""Auth + active-site resolution for MCP requests."""

from __future__ import annotations

from django.utils import timezone

from madga.models import Site, SiteUser, UserApiKey


def authenticate(request) -> tuple | None:
    """Return ``(user, api_key, site)`` or ``None`` on auth failure.

    Token format: ``Authorization: Bearer madga_<token>`` (same per-user
    keys minted in the studio's API keys page). The active Site is the
    user's first active membership; multi-site users use the
    ``set_active_site`` tool to switch — that just updates a session-like
    field on the UserApiKey itself so subsequent calls remember.
    """
    auth = (request.META.get("HTTP_AUTHORIZATION") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token.startswith("madga_"):
        return None

    key = UserApiKey.objects.filter(key=token, is_active=True).select_related("user").first()
    if key is None:
        return None

    key.last_used_at = timezone.now()
    key.save(update_fields=["last_used_at"])

    # Active site: pinned on UserApiKey.site if set, else first active
    # SiteUser membership, else (for superusers) the first active Site.
    site = None
    if key.site_id and key.site and key.site.is_active:
        if key.user.is_superuser or SiteUser.objects.filter(site=key.site, user=key.user).exists():
            site = key.site
    if site is None:
        membership = SiteUser.objects.filter(
            user=key.user, site__is_active=True,
        ).select_related("site").first()
        if membership:
            site = membership.site
        elif key.user.is_superuser:
            site = Site.objects.filter(is_active=True).order_by("id").first()

    return key.user, key, site


def user_can_access_site(user, site) -> bool:
    if site is None:
        return False
    if user.is_superuser:
        return True
    return SiteUser.objects.filter(user=user, site=site).exists()
