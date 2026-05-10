"""Helpers to convert ORM objects to API schemas."""

from .schemas import (
    AuthorSchema,
    CategorySchema,
    MediaSchema,
    PageDetailSchema,
    PostDetailSchema,
    PostListSchema,
    TagSchema,
)


def author_to_schema(user) -> AuthorSchema | None:
    if not user:
        return None
    full_name = (user.get_full_name() or "").strip()
    return AuthorSchema(id=user.id, username=user.username, full_name=full_name)


def category_to_schema(category) -> CategorySchema | None:
    if not category:
        return None
    return CategorySchema(
        id=category.id,
        name=category.name,
        slug=category.slug,
        color=category.color,
        description=category.description or "",
    )


def media_to_schema(media) -> MediaSchema | None:
    if not media:
        return None
    return MediaSchema(
        id=media.id,
        url=media.file.url if media.file else "",
        alt_text=media.alt_text or "",
        width=media.width,
        height=media.height,
    )


def post_list(post) -> PostListSchema:
    return PostListSchema(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt or "",
        status=post.status,
        published_at=post.published_at,
        views=post.views,
        category=category_to_schema(post.category),
        tags=[TagSchema(id=t.id, name=t.name, slug=t.slug) for t in post.tags.all()],
        featured_image=media_to_schema(post.featured_image),
        author=author_to_schema(post.author),
    )


def post_detail(post) -> PostDetailSchema:
    return PostDetailSchema(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt or "",
        status=post.status,
        published_at=post.published_at,
        views=post.views,
        category=category_to_schema(post.category),
        tags=[TagSchema(id=t.id, name=t.name, slug=t.slug) for t in post.tags.all()],
        featured_image=media_to_schema(post.featured_image),
        author=author_to_schema(post.author),
        body_html=post.body_html or "",
        meta_title=post.meta_title or "",
        meta_description=post.meta_description or "",
        og_image=media_to_schema(post.og_image),
        canonical_url=post.canonical_url or "",
    )


def page_detail(page) -> PageDetailSchema:
    return PageDetailSchema(
        id=page.id,
        title=page.title,
        slug=page.slug,
        body_html=page.body_html or "",
        layout=page.layout,
        meta_title=page.meta_title or "",
        meta_description=page.meta_description or "",
        updated_at=page.updated_at,
    )
