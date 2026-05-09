"""Main NinjaAPI registration for MADGA headless endpoints."""

import math
from typing import Optional

from django.db.models import Count, Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import NinjaAPI, Query

from madga.models import (
    Category,
    HomepageBlock,
    NavItem,
    Page,
    Post,
    Site,
    Tag,
)

from .auth import APIKeyAuth
from .schemas import (
    CategoryWithCountSchema,
    HomepageBlockSchema,
    NavItemSchema,
    PageDetailSchema,
    PaginatedPostsSchema,
    PostDetailSchema,
    TagSchema,
)
from .serializers import page_detail, post_detail, post_list

api = NinjaAPI(
    title="MADGA",
    version="0.1.0",
    description="Headless CMS API",
    urls_namespace="madga_api",
    docs_url="/docs",
)


def _resolve_site(request: HttpRequest) -> Site:
    """Determine the active Site from auth, host header, or first active."""
    site = getattr(request, "madga_site", None)
    if site:
        return site
    host = request.get_host().split(":")[0]
    site = Site.objects.filter(domain=host, is_active=True).first()
    if site:
        return site
    return Site.objects.filter(is_active=True).order_by("id").first()


def _public_qs(site: Site):
    return (
        Post.objects.alive()
        .filter(site=site, status=Post.STATUS_PUBLISHED)
        .filter(Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
        .select_related("category", "author", "featured_image")
        .prefetch_related("tags")
    )


@api.get("/posts/", response=PaginatedPostsSchema, auth=None)
def list_posts(
    request,
    page: int = 1,
    per_page: int = 20,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = Query(None, alias="search"),
):
    site = _resolve_site(request)
    if not site:
        return {"items": [], "page": 1, "per_page": per_page, "total": 0, "pages": 0}

    qs = _public_qs(site)
    if category:
        qs = qs.filter(category__slug=category)
    if tag:
        qs = qs.filter(tags__slug=tag).distinct()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(excerpt__icontains=search))

    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    total = qs.count()
    start = (page - 1) * per_page
    items = list(qs[start : start + per_page])

    return {
        "items": [post_list(p) for p in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": math.ceil(total / per_page) if total else 0,
    }


@api.get("/posts/{slug}/", response=PostDetailSchema, auth=None)
def get_post(request, slug: str):
    site = _resolve_site(request)
    post = get_object_or_404(_public_qs(site), slug=slug)
    return post_detail(post)


@api.post("/posts/{slug}/views/", auth=APIKeyAuth())
def increment_views(request, slug: str):
    from django.db.models import F

    site = _resolve_site(request)
    Post.objects.filter(site=site, slug=slug).update(views=F("views") + 1)
    return {"ok": True}


@api.get("/pages/{slug}/", response=PageDetailSchema, auth=None)
def get_page(request, slug: str):
    site = _resolve_site(request)
    page = get_object_or_404(
        Page.objects.filter(site=site, status=Post.STATUS_PUBLISHED), slug=slug
    )
    return page_detail(page)


@api.get("/categories/", response=list[CategoryWithCountSchema], auth=None)
def list_categories(request):
    site = _resolve_site(request)
    if not site:
        return []
    qs = (
        Category.objects.filter(site=site)
        .annotate(
            posts_count=Count(
                "posts",
                filter=Q(posts__status=Post.STATUS_PUBLISHED, posts__is_deleted=False),
            )
        )
        .order_by("name")
    )
    return [
        CategoryWithCountSchema(
            id=c.id,
            name=c.name,
            slug=c.slug,
            color=c.color,
            description=c.description or "",
            posts_count=c.posts_count,
        )
        for c in qs
    ]


@api.get("/tags/", response=list[TagSchema], auth=None)
def list_tags(request):
    site = _resolve_site(request)
    if not site:
        return []
    return [
        TagSchema(id=t.id, name=t.name, slug=t.slug)
        for t in Tag.objects.filter(site=site).order_by("name")
    ]


def _nav_to_schema(item: NavItem, children_map: dict) -> NavItemSchema:
    return NavItemSchema(
        id=item.id,
        label=item.label,
        url=item.url,
        open_in_new_tab=item.open_in_new_tab,
        sort_order=item.sort_order,
        children=[
            _nav_to_schema(c, children_map)
            for c in children_map.get(item.id, [])
        ],
    )


@api.get("/navigation/", response=list[NavItemSchema], auth=None)
def list_navigation(request):
    """Return the site's navigation as a nested tree (roots → children)."""
    site = _resolve_site(request)
    if not site:
        return []
    items = list(NavItem.objects.filter(site=site))
    children_map: dict[int, list[NavItem]] = {}
    roots: list[NavItem] = []
    for it in items:
        if it.parent_id is None:
            roots.append(it)
        else:
            children_map.setdefault(it.parent_id, []).append(it)
    # Already ordered by Meta.ordering on the model.
    return [_nav_to_schema(r, children_map) for r in roots]


@api.get("/homepage/", response=list[HomepageBlockSchema], auth=None)
def list_homepage_blocks(request):
    """Return ordered, visible homepage blocks for the active site."""
    site = _resolve_site(request)
    if not site:
        return []
    return [
        HomepageBlockSchema(
            id=b.id,
            block_type=b.block_type,
            config=b.config or {},
            sort_order=b.sort_order,
        )
        for b in HomepageBlock.objects.filter(site=site, is_visible=True)
    ]
