"""URL routes for the MADGA headless API (Django Ninja)."""

from django.urls import path

from .router import api

app_name = "madga_api"

urlpatterns = [
    path("", api.urls),
]
