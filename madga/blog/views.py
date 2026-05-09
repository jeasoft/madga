"""Public-facing blog views."""

from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
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
    """Return template lookup chain: theme-specific first, default fallback."""
    theme = (site.theme if site else "default") or "default"
    return [
        f"madga/themes/{theme}/{kind}.html",
        f"madga/blog/{kind}.html",
    ]


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


class HomepageView(TemplateView):
    """Public homepage. If the active Site has HomepageBlocks, render them;
    otherwise fall back to a generic recent-posts list.
    """

    def get_template_names(self):
        site = _resolve_site(self.request)
        theme = (site.theme if site else "default") or "default"
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
