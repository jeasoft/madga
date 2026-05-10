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

        # Resolve active site by host or fallback
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
