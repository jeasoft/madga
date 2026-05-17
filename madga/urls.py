"""URL helpers for projects mounting MADGA.

Idiomatic usage in your project's ``urls.py``::

    from django.urls import path, include
    from madga.urls import madga_public_urls
    from madga.api.router import api as madga_api

    urlpatterns = [
        path('studio/', include('madga.studio.urls')),
        path('api/madga/v1/', madga_api.urls),
        # ... your project-specific paths ...
        *madga_public_urls(),  # public blog + page + sitemap + rss + robots
    ]

The public routes mounted by ``madga_public_urls()``:

  /                  homepage (HomepageBlocks-driven; falls back if empty)
  /blog/             post list
  /blog/<slug>/      post detail
  /p/<slug>/         page detail
  /robots.txt
  /sitemap.xml
  /rss.xml

Pass ``include_homepage=False`` if your project owns ``/`` (e.g. a custom
LandingView). The other routes still register.
"""

from django.urls import path

from madga.blog.views import (
    HomepageView,
    PageDetailView,
    PostDetailView,
    PostListView,
    RobotsTxtView,
    RssFeedView,
    SitemapView,
)
from madga.blog.views_broadcast import UnsubscribeView
from madga.blog.views_forms import FormSubmitView


def madga_public_urls(*, include_homepage: bool = True) -> list:
    """Return the standard set of public-facing MADGA URL patterns."""
    patterns = []
    if include_homepage:
        patterns.append(path("", HomepageView.as_view(), name="madga_home"))
    patterns += [
        path("blog/", PostListView.as_view(), name="madga_post_list"),
        path("blog/<slug:slug>/", PostDetailView.as_view(), name="madga_post_detail"),
        path("p/<slug:slug>/", PageDetailView.as_view(), name="madga_page_detail"),
        path("robots.txt", RobotsTxtView.as_view(), name="madga_robots"),
        path("sitemap.xml", SitemapView.as_view(), name="madga_sitemap"),
        path("rss.xml", RssFeedView.as_view(), name="madga_rss"),
        path("madga/unsubscribe/<str:token>/", UnsubscribeView.as_view(), name="madga_unsubscribe"),
        path("madga/form/<int:block_id>/submit/", FormSubmitView.as_view(), name="madga_form_submit"),
    ]
    return patterns
