"""Role × action matrix: who can edit/delete what."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def people(db, site):
    User = get_user_model()
    from madga.models import SiteUser
    out = {}
    for username, role in [
        ("owner", "owner"),
        ("editor", "editor"),
        ("author", "author"),
        ("contrib", "contributor"),
    ]:
        u = User.objects.create_user(username=username, email=f"{username}@t.local", password="pw")
        SiteUser.objects.create(site=site, user=u, role=role)
        out[role] = u
    return out


def _client_for(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_author_cannot_edit_others_post(site, people):
    from madga.models import Post

    other = people["editor"]
    p = Post.objects.create(site=site, title="Editor's", slug="ed", author=other, status="draft")
    c = _client_for(people["author"])
    r = c.get(f"/studio/posts/{p.pk}/edit/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_author_can_edit_own_post(site, people):
    from madga.models import Post

    me = people["author"]
    p = Post.objects.create(site=site, title="Mine", slug="mine", author=me, status="draft")
    r = _client_for(me).get(f"/studio/posts/{p.pk}/edit/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_editor_can_edit_anyone(site, people):
    from madga.models import Post

    p = Post.objects.create(site=site, title="From author", slug="fa",
                            author=people["author"], status="draft")
    r = _client_for(people["editor"]).get(f"/studio/posts/{p.pk}/edit/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_author_can_publish_own_post(site, people):
    """Author has publish_post; saving as published goes through."""
    from madga.models import Post

    me = people["author"]
    p = Post.objects.create(site=site, title="Mine", slug="mine2", author=me, status="draft")
    r = _client_for(me).post(f"/studio/posts/{p.pk}/edit/", {
        "title": "Mine", "slug": "mine2", "body": "{}",
        "status": "published", "excerpt": "",
    })
    p.refresh_from_db()
    assert p.status == "published"


@pytest.mark.django_db
def test_author_cannot_delete_others_post(site, people):
    from madga.models import Post

    other = people["editor"]
    p = Post.objects.create(site=site, title="Editor's post", slug="ed-p",
                            author=other, status="published")
    r = _client_for(people["author"]).post(f"/studio/posts/{p.pk}/delete/")
    assert r.status_code == 403
    p.refresh_from_db()
    assert not p.is_deleted


@pytest.mark.django_db
def test_owner_can_delete_any(site, people):
    from madga.models import Post

    p = Post.objects.create(site=site, title="X", slug="x-by-author",
                            author=people["author"], status="published")
    r = _client_for(people["owner"]).post(f"/studio/posts/{p.pk}/delete/")
    assert r.status_code in (302, 200)
    p.refresh_from_db()
    assert p.is_deleted
