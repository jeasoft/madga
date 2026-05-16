"""API key auth for the MADGA headless API.

Two authentication paths:

  1. **Site key** (legacy): ``Site.api_key`` — anonymous access bound to
     a Site. ``request.user`` stays anonymous; only ``request.madga_site``
     is set.

  2. **Per-user key** (0.3.0+): ``UserApiKey.key`` — authenticates a
     specific User. Both ``request.user`` and ``request.madga_site`` get
     populated. Use this when the API needs to make per-user authorization
     decisions (own-content checks, audit trails).

Both flows accept ``Authorization: Bearer <key>``. Per-user keys are tried
first; if no match, falls back to site keys.
"""

from __future__ import annotations

from django.utils import timezone
from ninja.security import HttpBearer

from madga.models import Site, SiteUser, UserApiKey


class APIKeyAuth(HttpBearer):
    """Accepts either a UserApiKey or a Site.api_key."""

    def authenticate(self, request, token):
        # 1. Per-user key (prefix-checked to avoid an unindexed Site lookup).
        if token.startswith("madga_"):
            uk = (
                UserApiKey.objects.filter(key=token, is_active=True)
                .select_related("user", "site")
                .first()
            )
            if uk is not None:
                site = uk.site
                if site is None:
                    # Derive from user's first SiteUser membership.
                    su = SiteUser.objects.filter(user=uk.user).select_related("site").first()
                    site = su.site if su else None
                if site is None or not site.is_active:
                    return None
                request.madga_site = site
                request.user = uk.user
                request.madga_api_key = uk
                # Best-effort last_used update.
                UserApiKey.objects.filter(pk=uk.pk).update(last_used_at=timezone.now())
                return uk.user

        # 2. Site key (legacy / anonymous public-API access).
        site = Site.objects.filter(api_key=token, is_active=True).first()
        if site is None:
            return None
        request.madga_site = site
        return site
