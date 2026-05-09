"""Public-facing blog views."""

from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.generic import TemplateView, View

from madga.models import Category, Page, Post, Site, Tag


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
            "madga/blog/list.html",
            {
                "site": site,
                "posts": posts,
                "category": category,
                "tag": tag,
                "categories": Category.objects.filter(site=site).order_by("name"),
            },
        )


class PostDetailView(View):
    def get(self, request, slug):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        post = get_object_or_404(_public_posts(site), slug=slug)
        Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
        return render(
            request,
            "madga/blog/detail.html",
            {
                "site": site,
                "post": post,
            },
        )


class PageDetailView(View):
    def get(self, request, slug):
        site = _resolve_site(request)
        if site is None:
            raise Http404("No active site")
        page = get_object_or_404(
            Page.objects.filter(
                site=site, status=Post.STATUS_PUBLISHED
            ),
            slug=slug,
        )
        return render(
            request,
            "madga/blog/page.html",
            {"site": site, "page": page},
        )


class HomepageView(TemplateView):
    template_name = "madga/blog/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = _resolve_site(self.request)
        ctx["site"] = site
        if site:
            ctx["posts"] = _public_posts(site)[:9]
            ctx["pages"] = Page.objects.filter(
                site=site, status=Post.STATUS_PUBLISHED, parent__isnull=True
            ).order_by("sort_order")[:8]
        return ctx
