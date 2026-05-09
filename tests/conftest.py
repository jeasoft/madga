"""Test fixtures for MADGA's integration tests.

Each test gets a fresh in-memory site so we don't depend on global state
between runs.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def site(db):
    from madga.models import Site
    return Site.objects.create(
        name="Test Site",
        domain="testsite.local",
        description="A site under test.",
        theme="default",
    )


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    u = User.objects.create_user(
        username="admin", email="admin@test.local", password="adminpw"
    )
    u.is_staff = True
    u.is_superuser = True
    u.save()
    return u


@pytest.fixture
def client_logged_in(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c
