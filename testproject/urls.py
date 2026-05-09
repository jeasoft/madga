"""URL configuration for testproject."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from madga.api.router import api as madga_api

from . import prototype_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('studio/', include('madga.studio.urls')),
    path('api/madga/v1/', madga_api.urls),
    # django-allauth: headless JSON API (signup, login, password reset, MFA, ...)
    path('_allauth/', include('allauth.headless.urls')),
    # django-allauth: regular template-based flows (Studio doesn't use these,
    # but allauth still wants them registered for redirects/email links).
    path('accounts/', include('allauth.urls')),
    # Standalone CMS prototype mockup (Alpine.js + Tailwind, hardcoded data).
    # Lives in prototype/ at repo root; mounted here for browser preview.
    path('prototype/', prototype_views.prototype_index, name='prototype_index'),
    path('prototype/<str:name>', prototype_views.prototype_asset, name='prototype_asset'),
    path('blog/', include('madga.blog.urls')),
    path('', include('madga.blog.urls_root')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
