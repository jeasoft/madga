"""Middleware for the MADGA Studio."""

from django.shortcuts import redirect

from madga.models import Site, SiteUser


PUBLIC_STUDIO_PATHS = ("/studio/login/", "/studio/logout/", "/studio/accept-invite/")


class MadgaStudioMiddleware:
    """Resolve the active Site, attach a SiteUser membership (or 403)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith("/studio/"):
            return self.get_response(request)

        # Resolve the active Site for this request. Precedence:
        #   1. An upstream middleware or view already set ``request.madga_site``
        #      (e.g. host project mounts MADGA at /company/<slug>/studio/ and
        #      resolves the slug → Site). We respect that and don't overwrite.
        #   2. Session-pinned site from the workspace switcher.
        #   3. Host-based lookup (one Site per domain — classic single-tenant).
        #   4. Any active Site as last-resort fallback (single-Site projects).
        site = getattr(request, "madga_site", None)

        if site is None:
            session_site_id = request.session.get("madga_active_site_id")
            if session_site_id:
                site = Site.objects.filter(
                    id=session_site_id, is_active=True
                ).first()
                # Authorize: superusers always; otherwise must be a member.
                if site is not None and not request.user.is_superuser and request.user.is_authenticated:
                    if not SiteUser.objects.filter(site=site, user=request.user).exists():
                        site = None  # session pin was stale or unauthorized
                        request.session.pop("madga_active_site_id", None)

        if site is None:
            host = request.get_host().split(":")[0]
            site = Site.objects.filter(domain=host, is_active=True).first()

        if site is None:
            site = Site.objects.filter(is_active=True).order_by("id").first()

        request.madga_site = site

        # Public Studio pages don't need auth
        if any(path.startswith(p) for p in PUBLIC_STUDIO_PATHS):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(f"/studio/login/?next={path}")

        # Superusers always pass
        if request.user.is_superuser:
            request.madga_membership = None
            return self.get_response(request)

        if site is None:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden("No active MADGA site configured.")

        membership = SiteUser.objects.filter(site=site, user=request.user).first()
        if membership is None:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden(
                "You are not a member of this MADGA site."
            )
        request.madga_membership = membership
        return self.get_response(request)
