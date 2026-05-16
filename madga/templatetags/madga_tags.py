"""Template tags for embedding MADGA content in any Django template."""

from django import template
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe

from madga.models import Category, Post

register = template.Library()


@register.simple_tag
def get_recent_posts(limit: int = 5, site=None):
    qs = Post.objects.alive().filter(
        status=Post.STATUS_PUBLISHED
    ).filter(Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
    if site is not None:
        qs = qs.filter(site=site)
    return list(qs.select_related("category", "author")[:limit])


@register.simple_tag
def get_posts_by_category(slug: str, limit: int = 5, site=None):
    qs = Post.objects.alive().filter(
        status=Post.STATUS_PUBLISHED, category__slug=slug
    ).filter(Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
    if site is not None:
        qs = qs.filter(site=site)
    return list(qs.select_related("category", "author")[:limit])


@register.simple_tag
def get_categories(site=None):
    qs = Category.objects.all()
    if site is not None:
        qs = qs.filter(site=site)
    return list(qs)


def _resolve_madga_site(context):
    """Return the MADGA Site from the context, never the contrib.sites Site.

    Third-party views (notably allauth's signup/login) inject their own
    ``site`` value via ``get_context_data``, which is a ``django.contrib.sites``
    Site and breaks MADGA queries that filter by ``site=``. Prefer
    ``madga_site`` (set by our context processor), then fall back to the
    request attribute.
    """
    site = context.get("madga_site")
    if site is not None:
        return site
    request = context.get("request")
    if request is not None:
        return getattr(request, "madga_site", None)
    return None


@register.simple_tag(takes_context=True)
def get_header_nav_items(context):
    """Return top-level NavItems with location=header for the current Site."""
    from madga.models import NavItem
    site = _resolve_madga_site(context)
    if site is None:
        return []
    return list(
        NavItem.objects
        .filter(site=site, location="header", parent__isnull=True)
        .order_by("sort_order", "id")
    )


@register.simple_tag(takes_context=True)
def get_footer_nav_columns(context):
    """Return footer column NavItems (location=footer, no parent) with their children."""
    from madga.models import NavItem
    site = _resolve_madga_site(context)
    if site is None:
        return []
    return list(
        NavItem.objects
        .filter(site=site, location="footer", parent__isnull=True)
        .order_by("sort_order", "id")
        .prefetch_related("children")
    )


@register.inclusion_tag("madga/includes/site_tokens.html")
def madga_tokens(site):
    return {"site": site}


@register.inclusion_tag("madga/includes/tracking.html", takes_context=True)
def madga_tracking(context, site):
    """Render GA4 + Meta Pixel snippets if configured on the Site.

    Gated by the ``madga_consent`` cookie: trackers only fire if the
    visitor has explicitly accepted via the cookie banner. If no
    tracking is configured on the Site, this renders nothing.
    """
    request = context.get("request")
    consent = (
        request.COOKIES.get("madga_consent") if request is not None else None
    )
    return {"site": site, "consent": consent}


@register.inclusion_tag("madga/includes/cookie_banner.html", takes_context=True)
def madga_cookie_banner(context, site=None):
    """Render the GDPR-style cookie consent banner.

    Renders only when:
      - the Site has at least one tracker configured (GA4 or Pixel), AND
      - the visitor has neither accepted nor declined yet.

    The banner is a single self-contained `<div>` + inline JS that
    writes ``madga_consent=accepted|declined`` for 365 days and reloads
    the page on accept so trackers can fire.
    """
    request = context.get("request")
    site = site or context.get("site") or context.get("madga_site")
    consent = (
        request.COOKIES.get("madga_consent") if request is not None else None
    )
    has_tracker = bool(
        site and (
            getattr(site, "google_analytics_id", "")
            or getattr(site, "facebook_pixel_id", "")
        )
    )
    return {
        "site": site,
        "show": has_tracker and not consent,
    }


@register.simple_tag
def madga_seo(post_or_page):
    """Render <title> + <meta> tags for a Post or Page."""
    if not post_or_page:
        return ""
    title = getattr(post_or_page, "meta_title", "") or post_or_page.title
    desc = getattr(post_or_page, "meta_description", "") or getattr(
        post_or_page, "excerpt", ""
    )
    parts = [
        f"<title>{title}</title>",
        f'<meta name="description" content="{desc}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
    ]
    canonical = getattr(post_or_page, "canonical_url", "")
    if canonical:
        parts.append(f'<link rel="canonical" href="{canonical}">')
    og_image = getattr(post_or_page, "og_image", None)
    if og_image and og_image.file:
        parts.append(f'<meta property="og:image" content="{og_image.file.url}">')
    return mark_safe("\n".join(parts))
