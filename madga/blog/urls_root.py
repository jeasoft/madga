"""Root-level routes for the MADGA blog (homepage, static pages)."""

from django.urls import path

from .views import HomepageView, PageDetailView

urlpatterns = [
    path("", HomepageView.as_view(), name="madga_home"),
    path("p/<slug:slug>/", PageDetailView.as_view(), name="madga_page"),
]
