"""Headless API endpoints — list, detail, auth."""

from __future__ import annotations

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_post_list_returns_published_only(site):
    from django.test import Client
    from madga.models import Post

    Post.objects.create(
        site=site, title="Live", slug="live-1", status="published",
        published_at=timezone.now(),
    )
    Post.objects.create(
        site=site, title="Draft", slug="draft-1", status="draft",
    )

    r = Client().get("/api/madga/v1/posts/")
    assert r.status_code == 200
    payload = r.json()
    slugs = {p["slug"] for p in payload["items"]}
    assert "live-1" in slugs
    assert "draft-1" not in slugs


@pytest.mark.django_db
def test_post_detail_serialises_body(site):
    from django.test import Client
    from madga.models import Post

    p = Post.objects.create(
        site=site, title="X", slug="x", status="published",
        published_at=timezone.now(),
        body={"blocks": [{"type": "paragraph", "data": {"text": "hi"}}]},
    )
    p.save()  # signal regenerates body_html
    r = Client().get(f"/api/madga/v1/posts/{p.slug}/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["title"] == "X"
    assert "<p>hi</p>" in payload["body_html"]


@pytest.mark.django_db
def test_pages_endpoint(site):
    from django.test import Client
    from madga.models import Page

    Page.objects.create(
        site=site, title="About", slug="about", status="published",
        body={"blocks": [{"type": "paragraph", "data": {"text": "us"}}]},
    ).save()
    r = Client().get("/api/madga/v1/pages/about/")
    assert r.status_code == 200
    assert "us" in r.json().get("body_html", "")
