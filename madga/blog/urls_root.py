"""Root-level routes for the MADGA blog (homepage, static pages, feeds)."""

from django.urls import path

from .views import (
    HomepageView,
    PageDetailView,
    RobotsTxtView,
    RssFeedView,
    SitemapView,
)
from .views_broadcast import UnsubscribeView
from .views_forms import FormSubmitView

urlpatterns = [
    path("", HomepageView.as_view(), name="madga_home"),
    path("robots.txt", RobotsTxtView.as_view(), name="madga_robots"),
    path("sitemap.xml", SitemapView.as_view(), name="madga_sitemap"),
    path("rss.xml", RssFeedView.as_view(), name="madga_rss"),
    path("p/<slug:slug>/", PageDetailView.as_view(), name="madga_page"),
    path("madga/unsubscribe/<str:token>/", UnsubscribeView.as_view(), name="madga_unsubscribe"),
    path("madga/form/<int:block_id>/submit/", FormSubmitView.as_view(), name="madga_form_submit"),
]
