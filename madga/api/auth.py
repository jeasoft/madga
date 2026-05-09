"""API key auth for the MADGA headless API."""

from ninja.security import HttpBearer

from madga.models import Site


class APIKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            site = Site.objects.get(api_key=token, is_active=True)
        except Site.DoesNotExist:
            return None
        request.madga_site = site
        return site
