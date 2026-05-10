"""Verify Accept-Language switches the studio's UI language."""

from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_studio_renders_in_english_when_accept_language_en(client_logged_in):
    r = client_logged_in.get("/studio/dashboard/", HTTP_ACCEPT_LANGUAGE="en")
    body = r.content.decode()
    # English UI markers — sidebar items / topbar buttons / superuser tag.
    assert "Sign out" in body
    assert "Dashboard" in body
    # Spanish-only words should be ABSENT.
    assert "Salir" not in body


@pytest.mark.django_db
def test_studio_renders_in_spanish_when_accept_language_es(client_logged_in):
    r = client_logged_in.get("/studio/dashboard/", HTTP_ACCEPT_LANGUAGE="es")
    body = r.content.decode()
    # Spanish translation we provided for "Sign out".
    assert "Salir" in body
    assert "Sign out" not in body


@pytest.mark.django_db
def test_block_label_translates(site):
    from django.utils import translation
    from madga.blocks import get_block_type

    bt = get_block_type("text")
    with translation.override("es"):
        assert str(bt.label) == "Texto"
    with translation.override("en"):
        assert str(bt.label) == "Text"
