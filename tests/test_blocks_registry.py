"""Block registry: registration, default config, render dispatch."""

from __future__ import annotations

import pytest


def test_default_block_types_registered():
    from madga.blocks import all_block_types, get_block_type

    keys = {bt.key for bt in all_block_types()}
    assert {"hero", "recent_posts", "featured_post", "newsletter", "text", "cta"} <= keys
    bt = get_block_type("hero")
    assert bt is not None
    assert bt.label == "Hero"


def test_register_validates_required_attrs():
    from madga.blocks import BlockType, register_block_type

    class Missing(BlockType):
        # no key, no label, no template
        pass

    with pytest.raises(ValueError, match="key"):
        register_block_type(Missing)


def test_default_config_returns_field_defaults():
    from madga.blocks import get_block_type

    cfg = get_block_type("hero").default_config()
    assert cfg["title"] == "Bienvenido"
    assert cfg["cta_url"] == "/blog/"


@pytest.mark.django_db
def test_homepage_iterates_blocks(site):
    from django.test import Client
    from madga.models import HomepageBlock

    HomepageBlock.objects.create(
        site=site, block_type="hero", sort_order=1, is_visible=True,
        config={"title": "Hola registry", "subtitle": "ok",
                "cta_label": "ver", "cta_url": "/blog/"},
    )
    HomepageBlock.objects.create(
        site=site, block_type="text", sort_order=2, is_visible=True,
        config={"title": "intro", "body": "lorem ipsum"},
    )
    # Hidden block must NOT appear.
    HomepageBlock.objects.create(
        site=site, block_type="cta", sort_order=3, is_visible=False,
        config={"title": "secret", "cta_label": "?", "cta_url": "/"},
    )

    r = Client().get("/")
    assert r.status_code == 200
    body = r.content.decode()
    assert "Hola registry" in body
    assert "lorem ipsum" in body
    assert "secret" not in body  # hidden block doesn't render
