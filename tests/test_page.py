"""Page model + public render at /p/<slug>/."""

from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_page_create_and_render(client_logged_in, site):
    from madga.models import Page

    p = Page.objects.create(
        site=site, title="About", slug="about", status="published",
        body={"blocks": [{"type": "header", "data": {"text": "About us", "level": 2}}]},
    )
    p.save()  # signal renders body_html
    assert "<h2>About us</h2>" in (p.body_html or "")

    r = client_logged_in.get("/p/about/")
    assert r.status_code == 200
    assert b"About us" in r.content


@pytest.mark.django_db
def test_page_404_when_draft(client_logged_in, site):
    from madga.models import Page

    Page.objects.create(site=site, title="WIP", slug="wip", status="draft")
    r = client_logged_in.get("/p/wip/")
    assert r.status_code == 404
