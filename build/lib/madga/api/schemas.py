"""Schemas for the MADGA headless API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ninja import Schema


class AuthorSchema(Schema):
    id: int
    username: str
    full_name: str = ""


class CategorySchema(Schema):
    id: int
    name: str
    slug: str
    color: str
    description: str = ""


class CategoryWithCountSchema(CategorySchema):
    posts_count: int = 0


class TagSchema(Schema):
    id: int
    name: str
    slug: str


class MediaSchema(Schema):
    id: UUID
    url: str
    alt_text: str = ""
    width: Optional[int] = None
    height: Optional[int] = None


class PostListSchema(Schema):
    id: UUID
    title: str
    slug: str
    excerpt: str = ""
    status: str
    published_at: Optional[datetime] = None
    views: int = 0
    category: Optional[CategorySchema] = None
    tags: list[TagSchema] = []
    featured_image: Optional[MediaSchema] = None
    author: Optional[AuthorSchema] = None


class PostDetailSchema(PostListSchema):
    body_html: str = ""
    meta_title: str = ""
    meta_description: str = ""
    og_image: Optional[MediaSchema] = None
    canonical_url: str = ""


class PageDetailSchema(Schema):
    id: UUID
    title: str
    slug: str
    body_html: str = ""
    layout: str
    meta_title: str = ""
    meta_description: str = ""
    updated_at: datetime


class PaginatedPostsSchema(Schema):
    items: list[PostListSchema]
    page: int
    per_page: int
    total: int
    pages: int


class NavItemSchema(Schema):
    id: int
    label: str
    url: str
    open_in_new_tab: bool = False
    sort_order: int = 0
    children: list["NavItemSchema"] = []


class HomepageBlockSchema(Schema):
    id: int
    block_type: str
    config: dict[str, Any] = {}
    sort_order: int = 0


# Resolve forward reference for self-referential schema.
NavItemSchema.model_rebuild()
