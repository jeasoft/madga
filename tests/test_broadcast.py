"""Tests for the broadcast feature: Subscriber + BroadcastJob + email publisher."""

import pytest
from django.core import mail
from django.test import Client

from madga.models import BroadcastJob, Site, SiteUser, Subscriber
from madga.publishers import all_publishers, get_publisher
from madga.publishers.email import EmailSubscribersPublisher


@pytest.fixture
def site(db):
    return Site.objects.create(
        name="Test Site", domain="localhost", accent_color="#6C63FF"
    )


@pytest.fixture
def superuser(db, django_user_model):
    return django_user_model.objects.create_superuser(
        "admin", "admin@example.com", "pw"
    )


@pytest.fixture
def auth_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


@pytest.mark.django_db
def test_email_publisher_is_registered():
    pub = get_publisher("email_subscribers")
    assert pub is not None
    assert isinstance(pub, EmailSubscribersPublisher)
    assert pub in all_publishers()


@pytest.mark.django_db
def test_email_publisher_estimates_active_subscribers(site):
    Subscriber.objects.create(site=site, email="a@example.com", is_active=True)
    Subscriber.objects.create(site=site, email="b@example.com", is_active=True)
    Subscriber.objects.create(site=site, email="c@example.com", is_active=False)

    pub = get_publisher("email_subscribers")
    job = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="x", body_html="<p>x</p>",
    )
    assert pub.estimate_targets(job) == 2


@pytest.mark.django_db
def test_email_publisher_sends_to_active_subscribers(site):
    Subscriber.objects.create(site=site, email="a@example.com", is_active=True)
    Subscriber.objects.create(site=site, email="b@example.com", is_active=True)
    Subscriber.objects.create(site=site, email="c@example.com", is_active=False)

    job = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="Hello", body_html="<p>Hello world</p>", body_text="Hello world",
        targets_count=2,
    )
    mail.outbox = []
    pub = get_publisher("email_subscribers")
    result = pub.publish(job)

    assert result.sent == 2
    assert result.failed == 0
    assert len(mail.outbox) == 2
    # Unsubscribed one not contacted
    recipients = {m.to[0] for m in mail.outbox}
    assert recipients == {"a@example.com", "b@example.com"}
    # Has List-Unsubscribe header
    assert all("List-Unsubscribe" in m.extra_headers for m in mail.outbox)


@pytest.mark.django_db
def test_unsubscribe_view_marks_subscriber_inactive(site, client):
    sub = Subscriber.objects.create(site=site, email="x@example.com", is_active=True)
    token = sub.unsubscribe_token

    response = client.post(f"/madga/unsubscribe/{token}/")
    assert response.status_code == 200
    sub.refresh_from_db()
    assert sub.is_active is False
    assert sub.unsubscribed_at is not None


@pytest.mark.django_db
def test_broadcastjob_mark_finished_status_transitions(site):
    # all sent → STATUS_SENT
    job = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="x", targets_count=3, sent_count=3, failed_count=0,
    )
    job.mark_finished()
    assert job.status == BroadcastJob.STATUS_SENT

    # all failed → STATUS_FAILED
    job2 = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="x", targets_count=3, sent_count=0, failed_count=3,
    )
    job2.mark_finished()
    assert job2.status == BroadcastJob.STATUS_FAILED

    # mixed → STATUS_PARTIAL
    job3 = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="x", targets_count=3, sent_count=2, failed_count=1,
    )
    job3.mark_finished()
    assert job3.status == BroadcastJob.STATUS_PARTIAL


@pytest.mark.django_db
def test_subscriber_unsubscribe_method(site):
    sub = Subscriber.objects.create(site=site, email="z@example.com", is_active=True)
    sub.unsubscribe()
    assert sub.is_active is False
    assert sub.unsubscribed_at is not None


@pytest.mark.django_db
def test_studio_broadcast_create_sync_runs_job(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    Subscriber.objects.create(site=site, email="reader@example.com", is_active=True)

    mail.outbox = []
    response = auth_client.post(
        "/studio/broadcasts/new/",
        {
            "publisher_keys": ["email_subscribers"],
            "subject": "Manual broadcast",
            "body_html": "<p>Body</p>",
            "body_text": "Body",
        },
    )
    assert response.status_code == 302

    job = BroadcastJob.objects.filter(site=site).first()
    assert job is not None
    assert job.subject == "Manual broadcast"
    assert job.status == BroadcastJob.STATUS_SENT
    assert job.sent_count == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_studio_broadcast_create_requires_publisher(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    response = auth_client.post(
        "/studio/broadcasts/new/",
        {"subject": "x", "body_html": "x"},  # missing publisher_keys
    )
    assert response.status_code == 302
    assert BroadcastJob.objects.count() == 0


@pytest.mark.django_db
def test_subscriber_unique_per_site(site):
    Subscriber.objects.create(site=site, email="dup@example.com")
    with pytest.raises(Exception):
        Subscriber.objects.create(site=site, email="dup@example.com")


@pytest.mark.django_db
def test_subscriber_add_view_creates_subscriber(site, superuser, auth_client):
    SiteUser.objects.create(site=site, user=superuser, role=SiteUser.ROLE_OWNER)
    response = auth_client.post(
        "/studio/subscribers/add/",
        {"email": "new@example.com"},
    )
    assert response.status_code == 302
    assert Subscriber.objects.filter(site=site, email="new@example.com").exists()
