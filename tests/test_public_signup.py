"""Integration tests for the public allauth signup flow + MADGA signal bridge."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from madga.signals import user_post_signup


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_signup_page_renders_with_madga_chrome(client):
    response = client.get("/accounts/signup/")
    assert response.status_code == 200
    body = response.content.decode()
    # Site chrome wraps the form
    assert "Powered by" in body
    assert "<form" in body
    # i18n strings render (LANGUAGE_CODE=es)
    assert "Crear" in body or "Create" in body


@pytest.mark.django_db
def test_login_page_renders_with_madga_chrome(client):
    response = client.get("/accounts/login/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Powered by" in body
    assert "<form" in body


@pytest.mark.django_db
def test_public_signup_fires_user_post_signup_with_kind(client):
    """End-to-end: POST /accounts/signup/ -> User created + user_post_signup fired."""
    captured = []

    def receiver(sender, user, request, kind, **kw):
        captured.append({"user": user, "kind": kind})

    user_post_signup.connect(receiver)
    try:
        # Host project sets the kind in session via a pre-signup picker.
        # We simulate that here by writing directly to the session.
        session = client.session
        session["madga_signup_kind"] = "talent"
        session.save()

        response = client.post(
            "/accounts/signup/",
            {
                "email": "newbie@example.com",
                "username": "newbie",
                "password1": "Sup3rSecret!nope",
                "password2": "Sup3rSecret!nope",
            },
        )
        # Allauth redirects to LOGIN_REDIRECT_URL on success.
        # In this dev project that's /studio/, which 403s for non-members —
        # but the signup itself succeeded and the signal already fired.
        assert response.status_code in (200, 302)
        User = get_user_model()
        assert User.objects.filter(username="newbie").exists()

        assert len(captured) == 1, f"signal fired {len(captured)} times: {captured}"
        assert captured[0]["user"].username == "newbie"
        assert captured[0]["kind"] == "talent"
    finally:
        user_post_signup.disconnect(receiver)


@pytest.mark.django_db
def test_signup_without_kind_fires_signal_with_empty_kind(client):
    captured = []

    def receiver(sender, user, request, kind, **kw):
        captured.append(kind)

    user_post_signup.connect(receiver)
    try:
        client.post(
            "/accounts/signup/",
            {
                "email": "no-kind@example.com",
                "username": "nokind",
                "password1": "Sup3rSecret!nope",
                "password2": "Sup3rSecret!nope",
            },
        )
        assert captured == [""], f"expected one fire with empty kind, got {captured}"
    finally:
        user_post_signup.disconnect(receiver)
