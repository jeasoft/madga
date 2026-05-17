"""Built-in MCP tools.

Every tool takes ``ctx`` (ToolContext) + keyword args parsed from the
JSON-RPC request, and returns a Python value. The dispatcher turns
the return into MCP ``content`` blocks (text or json-encoded text).

Tools that mutate (create_post, publish_post, broadcast, …) require
the user have an active SiteUser membership. Superusers always pass.
Read tools just need a site.
"""

from __future__ import annotations

from .registry import ToolError, register_tool


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

@register_tool(
    name="list_sites",
    description=(
        "List every Site (workspace) the authenticated user can access. "
        "Returns id, name, domain, and whether each site is the user's "
        "current active site for MCP."
    ),
    input_schema={"type": "object", "properties": {}},
    requires_site=False,
)
def list_sites(ctx, **_):
    from madga.models import Site, SiteUser

    if ctx.user.is_superuser:
        sites = Site.objects.filter(is_active=True).order_by("name")
    else:
        sites = Site.objects.filter(
            is_active=True, memberships__user=ctx.user,
        ).distinct().order_by("name")
    active_id = ctx.site.id if ctx.site else None
    return {
        "sites": [
            {
                "id": str(s.id),
                "name": s.name,
                "domain": s.domain,
                "active": s.id == active_id,
            }
            for s in sites
        ],
    }


@register_tool(
    name="set_active_site",
    description=(
        "Switch which Site this MCP session reads + writes against. "
        "Persists on the UserApiKey so subsequent calls remember. "
        "Required arg: site_id (UUID)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "site_id": {"type": "string", "description": "UUID of the Site to activate"},
        },
        "required": ["site_id"],
    },
    requires_site=False,
)
def set_active_site(ctx, site_id: str | None = None, **_):
    if not site_id:
        raise ToolError("site_id is required")
    from madga.models import Site
    from .auth import user_can_access_site

    site = Site.objects.filter(id=site_id, is_active=True).first()
    if site is None:
        raise ToolError(f"No active Site with id {site_id}")
    if not user_can_access_site(ctx.user, site):
        raise ToolError("You don't belong to that workspace")

    ctx.api_key.site = site
    ctx.api_key.save(update_fields=["site"])
    return {"active_site": {"id": str(site.id), "name": site.name}}


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

def _post_dict(p) -> dict:
    return {
        "id": str(p.id),
        "title": p.title,
        "slug": p.slug,
        "status": p.status,
        "excerpt": p.excerpt,
        "views": p.views,
        "category": p.category.name if p.category_id else None,
        "tags": list(p.tags.values_list("name", flat=True)) if p.pk else [],
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "url": f"/blog/{p.slug}/" if p.slug else "",
    }


@register_tool(
    name="list_posts",
    description=(
        "List posts in the active Site. Optional filters: status (draft, "
        "published, scheduled, archived), search (substring on title/slug), "
        "limit (default 20, max 100)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["draft", "published", "scheduled", "archived"]},
            "search": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    },
)
def list_posts(ctx, status=None, search=None, limit=20, **_):
    from madga.models import Post
    qs = Post.objects.alive().filter(site=ctx.site).select_related("category")
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(slug__icontains=search)
    qs = qs.order_by("-updated_at")[: min(int(limit or 20), 100)]
    return {"posts": [_post_dict(p) for p in qs]}


@register_tool(
    name="get_post",
    description="Full detail of a single post (including body JSON + body_html).",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
)
def get_post(ctx, id=None, **_):
    if not id:
        raise ToolError("id is required")
    from madga.models import Post
    p = Post.objects.alive().filter(site=ctx.site, pk=id).first()
    if p is None:
        raise ToolError(f"Post {id} not found")
    data = _post_dict(p)
    data["body"] = p.body
    data["body_html"] = p.body_html
    data["meta_title"] = p.meta_title
    data["meta_description"] = p.meta_description
    return data


@register_tool(
    name="create_post",
    description=(
        "Create a new post in the active Site. Required: title. "
        "Optional: body_text (turned into a single paragraph block), "
        "excerpt, status (default 'draft'), category_slug, tag_slugs."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body_text": {"type": "string"},
            "excerpt": {"type": "string"},
            "status": {"type": "string", "enum": ["draft", "published", "scheduled", "archived"]},
            "category_slug": {"type": "string"},
            "tag_slugs": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title"],
    },
)
def create_post(ctx, title=None, body_text="", excerpt="", status="draft",
                category_slug=None, tag_slugs=None, **_):
    if not title:
        raise ToolError("title is required")
    from madga.models import Category, Post, Tag

    category = None
    if category_slug:
        category = Category.objects.filter(site=ctx.site, slug=category_slug).first()
        if category is None:
            raise ToolError(f"Category '{category_slug}' not found in this site")

    body = {"blocks": []}
    if body_text:
        body["blocks"].append({"type": "paragraph", "data": {"text": body_text}})

    post = Post.objects.create(
        site=ctx.site, author=ctx.user,
        title=title, body=body, excerpt=excerpt,
        status=status,
        category=category,
    )

    if tag_slugs:
        tags = list(Tag.objects.filter(site=ctx.site, slug__in=tag_slugs))
        if tags:
            post.tags.set(tags)

    return _post_dict(post)


@register_tool(
    name="publish_post",
    description="Set a draft / scheduled post's status to 'published'.",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
    requires_permission="publish_post",
)
def publish_post(ctx, id=None, **_):
    if not id:
        raise ToolError("id is required")
    from madga.models import Post
    from django.utils import timezone
    p = Post.objects.alive().filter(site=ctx.site, pk=id).first()
    if p is None:
        raise ToolError(f"Post {id} not found")
    p.status = Post.STATUS_PUBLISHED
    if not p.published_at:
        p.published_at = timezone.now()
    p.save()
    return _post_dict(p)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@register_tool(
    name="list_pages",
    description="List static pages in the active Site.",
    input_schema={"type": "object", "properties": {}},
)
def list_pages(ctx, **_):
    from madga.models import Page
    pages = Page.objects.filter(site=ctx.site).order_by("sort_order", "title")
    return {
        "pages": [
            {
                "id": str(p.id),
                "title": p.title,
                "slug": p.slug,
                "status": p.status,
                "layout": p.layout,
                "url": f"/p/{p.slug}/" if p.slug else "",
            }
            for p in pages
        ],
    }


# ---------------------------------------------------------------------------
# Audience
# ---------------------------------------------------------------------------

@register_tool(
    name="list_subscribers",
    description=(
        "List email subscribers for the active Site. Optional: active "
        "(default true), search (substring on email), limit (default 50, max 500)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "active": {"type": "boolean"},
            "search": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
        },
    },
)
def list_subscribers(ctx, active=True, search=None, limit=50, **_):
    from madga.models import Subscriber
    qs = Subscriber.objects.filter(site=ctx.site)
    if active is not None:
        qs = qs.filter(is_active=bool(active))
    if search:
        qs = qs.filter(email__icontains=search)
    qs = qs.order_by("-created_at")[: min(int(limit or 50), 500)]
    return {
        "subscribers": [
            {
                "id": str(s.id),
                "email": s.email,
                "active": s.is_active,
                "source": s.source,
                "created_at": s.created_at.isoformat(),
            }
            for s in qs
        ],
    }


@register_tool(
    name="list_form_submissions",
    description=(
        "List public form submissions (ContactFormBlock inbox) for the "
        "active Site. Optional: form_key, unread_only, limit (default 50, max 500)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "form_key": {"type": "string"},
            "unread_only": {"type": "boolean"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
        },
    },
)
def list_form_submissions(ctx, form_key=None, unread_only=False, limit=50, **_):
    from madga.models import FormSubmission
    qs = FormSubmission.objects.filter(site=ctx.site)
    if form_key:
        qs = qs.filter(form_key=form_key)
    if unread_only:
        qs = qs.filter(is_read=False)
    qs = qs.order_by("-created_at")[: min(int(limit or 50), 500)]
    return {
        "submissions": [
            {
                "id": str(s.id),
                "form_key": s.form_key,
                "is_read": s.is_read,
                "data": s.data,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat(),
            }
            for s in qs
        ],
    }


# ---------------------------------------------------------------------------
# Channels + broadcasts
# ---------------------------------------------------------------------------

@register_tool(
    name="list_channels",
    description=(
        "List the active Site's connected social/email channels with "
        "publisher key, handle, audience size, last used, and active status."
    ),
    input_schema={"type": "object", "properties": {}},
)
def list_channels(ctx, **_):
    from madga.models import PublisherAccount
    accts = PublisherAccount.objects.filter(site=ctx.site).order_by("publisher_key")
    return {
        "channels": [
            {
                "id": str(a.id),
                "publisher_key": a.publisher_key,
                "handle": a.handle,
                "display_name": a.display_name,
                "active": a.is_active,
                "audience_size": a.audience_size,
                "last_used_at": a.last_used_at.isoformat() if a.last_used_at else None,
            }
            for a in accts
        ],
    }


@register_tool(
    name="list_broadcasts",
    description="Recent broadcast jobs for the active Site (default 20, max 100).",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "status": {"type": "string"},
        },
    },
)
def list_broadcasts(ctx, limit=20, status=None, **_):
    from madga.models import BroadcastJob
    qs = BroadcastJob.objects.filter(site=ctx.site)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by("-created_at")[: min(int(limit or 20), 100)]
    return {
        "broadcasts": [
            {
                "id": str(b.id),
                "publisher_key": b.publisher_key,
                "subject": b.subject,
                "status": b.status,
                "targets": b.targets_count,
                "sent": b.sent_count,
                "failed": b.failed_count,
                "created_at": b.created_at.isoformat(),
            }
            for b in qs
        ],
    }


@register_tool(
    name="broadcast",
    description=(
        "Fan out a broadcast for a post (or a standalone announcement) to "
        "one or more registered publishers. Required: publisher_keys (list). "
        "Either post_id or subject + body_text. Optional: schedule_at (ISO datetime; "
        "leave empty to send immediately)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "publisher_keys": {"type": "array", "items": {"type": "string"}},
            "post_id": {"type": "string"},
            "subject": {"type": "string"},
            "body_text": {"type": "string"},
            "schedule_at": {"type": "string", "description": "ISO 8601 datetime"},
        },
        "required": ["publisher_keys"],
    },
)
def broadcast(ctx, publisher_keys=None, post_id=None, subject=None,
              body_text="", schedule_at=None, **_):
    if not publisher_keys:
        raise ToolError("publisher_keys is required (at least one publisher key)")
    from madga.models import BroadcastJob, Post
    from madga.publishers import get_publisher
    from madga.studio.views.broadcasts import _FakeJobForEstimate, _worker_run

    post = None
    if post_id:
        post = Post.objects.alive().filter(site=ctx.site, pk=post_id).first()
        if post is None:
            raise ToolError(f"Post {post_id} not found")
    if not subject and post:
        subject = post.title
    if not subject:
        raise ToolError("subject is required when no post_id is given")

    related_url = ""
    if post and post.slug:
        domain = (ctx.site.domain or "").strip()
        scheme = "https" if domain and domain != "localhost" else "http"
        if domain and not domain.startswith("http"):
            related_url = f"{scheme}://{domain}/blog/{post.slug}/"
        else:
            related_url = f"/blog/{post.slug}/"

    created = []
    for key in publisher_keys:
        publisher = get_publisher(key)
        if publisher is None:
            raise ToolError(f"Publisher '{key}' is not registered")
        targets = publisher.estimate_targets(_FakeJobForEstimate(site=ctx.site))
        job = BroadcastJob.objects.create(
            site=ctx.site,
            publisher_key=key,
            subject=subject,
            body_html=post.body_html if post else f"<p>{body_text}</p>",
            body_text=body_text or (post.excerpt if post else ""),
            related_url=related_url,
            related_post=post,
            targets_count=targets,
            scheduled_at=schedule_at or None,
            created_by=ctx.user if ctx.user.is_authenticated else None,
        )
        created.append(job)

    # Run synchronously if not scheduled (mirrors the studio drawer behavior)
    from django.utils import timezone
    now = timezone.now()
    for job in created:
        if not job.scheduled_at or job.scheduled_at <= now:
            _worker_run(job)

    return {
        "broadcasts": [
            {
                "id": str(j.id),
                "publisher_key": j.publisher_key,
                "status": j.status,
                "sent": j.sent_count,
                "failed": j.failed_count,
            }
            for j in created
        ],
    }
