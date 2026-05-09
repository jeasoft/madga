"""Invitation lifecycle — create, accept, expire."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_invitation_creation_via_studio(client_logged_in, site, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core import mail
    from madga.models import UserInvitation

    r = client_logged_in.post(
        "/studio/users/invite/",
        {"email": "newperson@test.local", "role": "editor"},
        follow=True,
    )
    assert r.status_code == 200
    inv = UserInvitation.objects.get(email="newperson@test.local")
    assert inv.status == "pending"
    assert len(mail.outbox) == 1
    assert "Te invitaron" in mail.outbox[0].subject
    assert inv.token in mail.outbox[0].body


@pytest.mark.django_db
def test_accept_invite_creates_membership(site):
    from django.contrib.auth import get_user_model
    from django.test import Client
    from madga.models import SiteUser, UserInvitation

    inv = UserInvitation.objects.create(site=site, email="me@test.local", role="author")
    r = Client().post(f"/studio/accept-invite/{inv.token}/", follow=False)
    assert r.status_code == 302

    inv.refresh_from_db()
    assert inv.status == "accepted"
    assert inv.accepted_at is not None

    user = get_user_model().objects.get(email="me@test.local")
    assert SiteUser.objects.filter(site=site, user=user, role="author").exists()


@pytest.mark.django_db
def test_accept_expired_invitation(site):
    from django.test import Client
    from madga.models import UserInvitation

    inv = UserInvitation.objects.create(site=site, email="old@test.local", role="author")
    UserInvitation.objects.filter(pk=inv.pk).update(
        created_at=timezone.now() - timedelta(days=30)
    )

    r = Client().get(f"/studio/accept-invite/{inv.token}/")
    assert r.status_code == 200
    assert b"vencida" in r.content
    inv.refresh_from_db()
    assert inv.status == "expired"


@pytest.mark.django_db
def test_accept_invalid_token_404_friendly(site):
    from django.test import Client

    r = Client().get("/studio/accept-invite/this-is-not-a-real-token/")
    assert r.status_code == 200  # we render a friendly "not found" page
    assert b"no encontrada" in r.content
