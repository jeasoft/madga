"""Post lifecycle: draft → publish → public render."""

from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_post_create_draft_then_publish(client_logged_in, site):
    from madga.models import Post

    # Create a draft via the studio.
    r = client_logged_in.post(
        "/studio/posts/new/",
        {
            "title": "Hello world",
            "slug": "",  # auto-generate
            "body": '{"blocks":[{"type":"paragraph","data":{"text":"hola"}}]}',
            "status": "draft",
            "excerpt": "",
        },
        follow=True,
    )
    assert r.status_code == 200
    p = Post.objects.get(title="Hello world")
    assert p.status == "draft"
    assert p.slug == "hello-world"

    # Publishing populates published_at and renders body_html.
    r2 = client_logged_in.post(
        f"/studio/posts/{p.pk}/edit/",
        {
            "title": "Hello world",
            "slug": "hello-world",
            "body": '{"blocks":[{"type":"paragraph","data":{"text":"hola"}}]}',
            "status": "published",
            "excerpt": "",
        },
        follow=True,
    )
    assert r2.status_code == 200
    p.refresh_from_db()
    assert p.status == "published"
    assert p.published_at is not None
    assert "<p>hola</p>" in (p.body_html or "")


@pytest.mark.django_db
def test_post_detail_404_when_draft(client_logged_in, site):
    """Public detail view should 404 for a draft post."""
    from madga.models import Post

    p = Post.objects.create(
        site=site, title="Draft", slug="draft", status="draft", author=None,
    )
    r = client_logged_in.get(f"/blog/{p.slug}/")
    assert r.status_code == 404


@pytest.mark.django_db
def test_post_detail_200_when_published(client_logged_in, site):
    from django.utils import timezone
    from madga.models import Post

    p = Post.objects.create(
        site=site, title="Live", slug="live", status="published",
        published_at=timezone.now(), author=None,
        body={"blocks": [{"type": "paragraph", "data": {"text": "ok"}}]},
    )
    p.save()  # signal regenerates body_html
    r = client_logged_in.get("/blog/live/")
    assert r.status_code == 200
    assert b"<p>ok</p>" in r.content
