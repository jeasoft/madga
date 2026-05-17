"""Tests for ContactFormBlock + FormSubmission + public submit endpoint."""

import pytest
from django.core import mail
from django.test import Client

from madga.models import FormSubmission, HomepageBlock, Site, WebhookEndpoint


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test", domain="localhost")


@pytest.fixture
def form_block(site):
    return HomepageBlock.objects.create(
        site=site, block_type="contact_form",
        config={
            "title": "Contact us",
            "recipient_email": "leads@aplica.do",
            "form_key": "contact",
            "success_message": "Thanks!",
        },
        sort_order=1,
    )


@pytest.mark.django_db
def test_form_submit_creates_submission_and_redirects(form_block, site, client):
    response = client.post(
        f"/madga/form/{form_block.id}/submit/",
        {
            "name": "Juan",
            "email": "juan@example.com",
            "message": "Quiero info de un puesto",
            "source": "/blog/",
        },
    )
    assert response.status_code == 302
    assert "submitted=" in response["Location"]

    sub = FormSubmission.objects.get()
    assert sub.site == site
    assert sub.form_key == "contact"
    assert sub.data["name"] == "Juan"
    assert sub.data["email"] == "juan@example.com"
    assert sub.data["message"] == "Quiero info de un puesto"
    # Source field excluded from data payload
    assert "source" not in sub.data
    assert sub.source_url == "/blog/"


@pytest.mark.django_db
def test_form_submit_emails_recipient(form_block, site, client):
    mail.outbox = []
    client.post(
        f"/madga/form/{form_block.id}/submit/",
        {"name": "Juan", "email": "juan@example.com", "message": "hi"},
    )
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["leads@aplica.do"]
    assert "juan@example.com" in msg.body
    assert "contact" in msg.subject.lower()


@pytest.mark.django_db
def test_form_submit_fires_form_submitted_webhook(form_block, site, client):
    WebhookEndpoint.objects.create(
        site=site, url="https://aplica.do/hook",
        events=["form.submitted"], is_active=True,
    )
    client.post(
        f"/madga/form/{form_block.id}/submit/",
        {"name": "Juan", "email": "juan@example.com", "message": "x"},
    )
    from madga.models import WebhookDelivery
    d = WebhookDelivery.objects.get()
    assert d.event == "form.submitted"
    assert d.payload["data"]["email"] == "juan@example.com"
    assert d.payload["form_key"] == "contact"


@pytest.mark.django_db
def test_honeypot_silently_drops_bot_submission(form_block, client):
    response = client.post(
        f"/madga/form/{form_block.id}/submit/",
        {
            "name": "Bot",
            "email": "bot@example.com",
            "message": "spam",
            "website": "http://spam.com",  # honeypot
        },
    )
    assert response.status_code == 200  # JsonResponse
    assert FormSubmission.objects.count() == 0


@pytest.mark.django_db
def test_form_submit_json_request_gets_json_response(form_block, client):
    response = client.post(
        f"/madga/form/{form_block.id}/submit/",
        {"name": "Juan", "email": "j@e.com", "message": "x"},
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    data = response.json()
    assert data["ok"] is True
    assert "id" in data


@pytest.mark.django_db
def test_form_block_is_registered():
    from madga.blocks import get_block_type
    bt = get_block_type("contact_form")
    assert bt is not None
    assert any(f.name == "recipient_email" for f in bt.fields)
    assert any(f.name == "form_key" for f in bt.fields)


@pytest.mark.django_db
def test_inbox_marks_unread_visible(form_block, site, client, django_user_model):
    user = django_user_model.objects.create_superuser("admin", "a@e.com", "p")
    from madga.models import SiteUser
    SiteUser.objects.create(site=site, user=user, role=SiteUser.ROLE_OWNER)

    FormSubmission.objects.create(
        site=site, form_key="contact", data={"email": "u@e.com"}, is_read=False,
    )

    c = Client()
    c.force_login(user)
    response = c.get("/studio/inbox/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "u@e.com" in body
