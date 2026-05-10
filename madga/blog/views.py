"""Public-facing blog views."""

from django.db.models import F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.feedgenerator import Rss201rev2Feed
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView, View

from madga.models import Category, HomepageBlock, Page, Post, Site, Tag


def _resolve_site(request) -> Site | None:
    site = getattr(request, "madga_site", None)
    if site:
        return site
    host = request.get_host().split(":")[0]
    return (
        Site.objects.filter(domain=host, is_active=True).first()
        or Site.objects.filter(is_active=True).order_by("id").first()
    )


def _public_posts(site: Site):
    return (
        Post.objects.alive()
        .filter(site=site, status=Post.STATUS_PUBLISHED)
        .filter(Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
        .select_related("category", "author", "featured_image")
        .prefetch_related("tags")
    )


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PostListView(View):
    def get(self, request):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        posts = _public_posts(site)
        category_slug = request.GET.get("category")
        tag_slug = request.GET.get("tag")
        category = None
        tag = None
        if category_slug:
            category = get_object_or_404(Category, site=site, slug=category_slug)
            posts = posts.filter(category=category)
        if tag_slug:
            tag = get_object_or_404(Tag, site=site, slug=tag_slug)
            posts = posts.filter(tags=tag)
        return render(
            request,
            _themed_templates(site, "list"),
            {
                "site": site,
                "posts": posts,
                "category": category,
                "tag": tag,
                "categories": Category.objects.filter(site=site).order_by("name"),
            },
        )


def _themed_templates(site, kind: str):
    """Return template lookup chain: theme-specific first, default fallback.

    If the Site has a ``layout_<kind>`` set in ``settings``, the chain prefers
    ``<kind>-<layout>.html`` so users can pick a layout per content-type
    from /studio/layouts/.
    """
    theme = (site.theme if site else "default") or "default"
    chain = []
    if site:
        layout = (site.settings or {}).get(f"layout_{kind}")
        if layout and layout != "default":
            chain.append(f"madga/themes/{theme}/{kind}-{layout}.html")
            chain.append(f"madga/blog/{kind}-{layout}.html")
    chain += [
        f"madga/themes/{theme}/{kind}.html",
        f"madga/blog/{kind}.html",
    ]
    return chain


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PostDetailView(View):
    def get(self, request, slug):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        post = get_object_or_404(_public_posts(site), slug=slug)
        Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
        return render(
            request,
            _themed_templates(site, "detail"),
            {"site": site, "post": post},
        )


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PageDetailView(View):
    def get(self, request, slug):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        page = get_object_or_404(
            Page.objects.filter(site=site, status=Post.STATUS_PUBLISHED),
            slug=slug,
        )
        # Layout chain: theme/page-{layout}.html → theme/page.html → default page.html
        theme = (site.theme if site else "default") or "default"
        layout = page.layout or "simple"
        return render(
            request,
            [
                f"madga/themes/{theme}/page-{layout}.html",
                f"madga/themes/{theme}/page.html",
                "madga/blog/page.html",
            ],
            {"site": site, "page": page},
        )


def _absolute(request, path: str) -> str:
    return request.build_absolute_uri(path)


class RobotsTxtView(View):
    """Plain-text robots.txt pointing to the site's sitemap."""

    def get(self, request):
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /studio/\n"
            "Disallow: /api/\n"
            f"Sitemap: {_absolute(request, '/sitemap.xml')}\n"
        )
        return HttpResponse(body, content_type="text/plain; charset=utf-8")


class SitemapView(View):
    """Hand-rolled sitemap.xml — no django.contrib.sitemaps dependency."""

    def get(self, request):
        site = _resolve_site(request)
        urls = [_absolute(request, "/"), _absolute(request, "/blog/")]
        if site:
            for slug in _public_posts(site).values_list("slug", flat=True):
                urls.append(_absolute(request, f"/blog/{slug}/"))
            for slug in (
                Page.objects.filter(site=site, status=Post.STATUS_PUBLISHED)
                .values_list("slug", flat=True)
            ):
                urls.append(_absolute(request, f"/p/{slug}/"))
        body = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            body.append(f"  <url><loc>{u}</loc></url>")
        body.append("</urlset>")
        return HttpResponse("\n".join(body), content_type="application/xml; charset=utf-8")


class RssFeedView(View):
    """RSS 2.0 feed of the latest 30 published posts."""

    def get(self, request):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        feed = Rss201rev2Feed(
            title=site.name,
            link=_absolute(request, "/"),
            description=site.description or site.meta_description or site.name,
            language="es",
        )
        for p in _public_posts(site)[:30]:
            feed.add_item(
                title=p.title,
                link=_absolute(request, f"/blog/{p.slug}/"),
                description=(p.excerpt or "")[:500],
                pubdate=p.published_at,
                unique_id=str(p.id),
                author_name=(p.author.get_full_name() or p.author.username) if p.author_id else "",
            )
        return HttpResponse(
            feed.writeString("utf-8"), content_type="application/rss+xml; charset=utf-8"
        )


@method_decorator(xframe_options_sameorigin, name="dispatch")
class HomepageView(TemplateView):
    """Public homepage. If the active Site has HomepageBlocks, render them;
    otherwise fall back to a generic recent-posts list.

    First-run: if no Site exists at all, render a friendly welcome page
    pointing to the studio + the create_site command.
    """

    def get_template_names(self):
        site = _resolve_site(self.request)
        if site is None:
            return ["madga/blog/first_run.html"]
        theme = site.theme or "default"
        return [
            f"madga/themes/{theme}/home.html",
            "madga/blog/home.html",
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = _resolve_site(self.request)
        ctx["site"] = site
        if site:
            blocks = list(
                HomepageBlock.objects.filter(site=site, is_visible=True).order_by(
                    "sort_order", "id"
                )
            )
            # Resolve referenced data per block_type so templates stay dumb.
            for b in blocks:
                cfg = b.config or {}
                if b.block_type == HomepageBlock.BLOCK_RECENT_POSTS:
                    count = max(1, min(int(cfg.get("count") or 3), 12))
                    b.resolved = list(_public_posts(site)[:count])
                elif b.block_type == HomepageBlock.BLOCK_FEATURED_POST:
                    slug = cfg.get("slug") or ""
                    b.resolved = (
                        _public_posts(site).filter(slug=slug).first() if slug else None
                    )
                else:
                    b.resolved = None
            ctx["blocks"] = blocks
            ctx["has_blocks"] = bool(blocks)
            ctx["posts"] = _public_posts(site)[:9]
            ctx["pages"] = Page.objects.filter(
                site=site, status=Post.STATUS_PUBLISHED, parent__isnull=True
            ).order_by("sort_order")[:8]
        return ctx
