"""URL config for the miscoreblog project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from madga.api.router import api as madga_api
from madga.blog.views import (
    PostDetailView,
    PostListView,
    RobotsTxtView,
    RssFeedView,
    SitemapView,
)

from .views import LandingView, PrivacidadView, TerminosView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('studio/', include('madga.studio.urls')),
    path('api/madga/v1/', madga_api.urls),
    path('_allauth/', include('allauth.headless.urls')),
    path('accounts/', include('allauth.urls')),

    # Public miscore pages take precedence over MADGA's generic homepage.
    path('', LandingView.as_view(), name='miscore_home'),
    path('privacidad/', PrivacidadView.as_view(), name='miscore_privacidad'),
    path('terminos/', TerminosView.as_view(), name='miscore_terminos'),

    # MADGA blog + feeds, mounted under /blog/ for now.
    path('blog/', PostListView.as_view(), name='post_list'),
    path('blog/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('robots.txt', RobotsTxtView.as_view(), name='madga_robots'),
    path('sitemap.xml', SitemapView.as_view(), name='madga_sitemap'),
    path('rss.xml', RssFeedView.as_view(), name='madga_rss'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
