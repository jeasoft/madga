"""Tests for the auto-broadcast-on-publish flow + real publishers."""

from unittest.mock import patch

import pytest

from madga.models import BroadcastJob, Post, PublisherAccount, Site
from madga.publishers import get_publisher


@pytest.fixture
def site(db):
    return Site.objects.create(name="Test", domain="localhost")


@pytest.mark.django_db
def test_queued_on_publish_fires_when_post_transitions_to_published(site, django_user_model):
    user = django_user_model.objects.create_user("a", "a@e.com", "p")
    post = Post.objects.create(site=site, title="Hi", status=Post.STATUS_DRAFT, author=user)

    job = BroadcastJob.objects.create(
        site=site,
        publisher_key="email_subscribers",
        subject="Hi",
        body_html="<p>x</p>",
        body_text="x",
        related_post=post,
        status=BroadcastJob.STATUS_QUEUED_ON_PUBLISH,
        targets_count=0,
    )

    # Transition to published
    post.status = Post.STATUS_PUBLISHED
    post.save()

    job.refresh_from_db()
    assert job.status in (
        BroadcastJob.STATUS_SENT,
        BroadcastJob.STATUS_PARTIAL,
        BroadcastJob.STATUS_FAILED,
    )


@pytest.mark.django_db
def test_queued_on_publish_unaffected_when_post_stays_draft(site, django_user_model):
    user = django_user_model.objects.create_user("a", "a@e.com", "p")
    post = Post.objects.create(site=site, title="Hi", status=Post.STATUS_DRAFT, author=user)

    job = BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="Hi", body_html="x", body_text="x",
        related_post=post,
        status=BroadcastJob.STATUS_QUEUED_ON_PUBLISH,
    )

    post.title = "Edited"
    post.save()  # still draft

    job.refresh_from_db()
    assert job.status == BroadcastJob.STATUS_QUEUED_ON_PUBLISH


@pytest.mark.django_db
def test_already_published_post_save_doesnt_refire(site, django_user_model):
    user = django_user_model.objects.create_user("a", "a@e.com", "p")
    post = Post.objects.create(site=site, title="Hi", status=Post.STATUS_PUBLISHED, author=user)
    # No queued jobs to begin with
    BroadcastJob.objects.create(
        site=site, publisher_key="email_subscribers",
        subject="Hi", body_html="x", body_text="x",
        related_post=post,
        status=BroadcastJob.STATUS_SENT,
    )
    # Edit
    post.title = "Hi 2"
    post.save()
    assert BroadcastJob.objects.filter(related_post=post, status=BroadcastJob.STATUS_SENT).count() == 1


# ---------------------------------------------------------------------------
# Real Mastodon publisher
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mastodon_publish_posts_status(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="mastodon", handle="@me@hachyderm.io", is_active=True,
    )
    acct.set_credentials({"instance_url": "https://hachyderm.io", "access_token": "T"})
    acct.save()

    job = BroadcastJob.objects.create(
        site=site, publisher_key="mastodon",
        subject="Hello", body_text="Hello world",
        targets_count=1,
    )

    pub = get_publisher("mastodon")
    with patch("madga.publishers.social._http_post_form") as mock_post:
        mock_post.return_value = {"id": "999"}
        result = pub.publish(job)

    assert result.sent == 1
    assert result.failed == 0
    args, _ = mock_post.call_args
    assert "hachyderm.io/api/v1/statuses" in args[0]
    assert args[1]["status"] == "Hello world"
    assert "Bearer T" in args[2]["Authorization"]


@pytest.mark.django_db
def test_mastodon_publish_fails_when_credentials_missing(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="mastodon", handle="@me", is_active=True,
    )
    # No credentials saved
    job = BroadcastJob.objects.create(
        site=site, publisher_key="mastodon",
        subject="Hello", body_text="Hello",
        targets_count=1,
    )
    pub = get_publisher("mastodon")
    result = pub.publish(job)
    assert result.failed == 1


# ---------------------------------------------------------------------------
# Real Bluesky publisher
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_bluesky_publish_does_login_and_create_record(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="bluesky", handle="me.bsky.social", is_active=True,
    )
    acct.set_credentials({"handle": "me.bsky.social", "app_password": "P"})
    acct.save()

    job = BroadcastJob.objects.create(
        site=site, publisher_key="bluesky",
        subject="Hello", body_text="Hi Bluesky",
        targets_count=1,
    )

    pub = get_publisher("bluesky")
    with patch("madga.publishers.social._http_post_json") as mock_post:
        # first call → createSession; second → createRecord
        mock_post.side_effect = [
            {"accessJwt": "JWT", "did": "did:plc:abc"},
            {"uri": "at://did:plc:abc/app.bsky.feed.post/x"},
        ]
        result = pub.publish(job)

    assert result.sent == 1
    assert mock_post.call_count == 2
    # First call: createSession
    assert "createSession" in mock_post.call_args_list[0][0][0]
    # Second call: createRecord with Bearer token
    assert "createRecord" in mock_post.call_args_list[1][0][0]
    assert "Bearer JWT" in mock_post.call_args_list[1][0][2]["Authorization"]


@pytest.mark.django_db
def test_bluesky_test_connection_calls_create_session(site):
    acct = PublisherAccount.objects.create(
        site=site, publisher_key="bluesky", handle="me.bsky.social", is_active=True,
    )
    acct.set_credentials({"handle": "me.bsky.social", "app_password": "P"})
    acct.save()

    pub = get_publisher("bluesky")
    with patch("madga.publishers.social._http_post_json") as mock_post:
        mock_post.return_value = {"accessJwt": "x", "did": "did:plc:abc"}
        ok, msg = pub.test_connection(acct)
    assert ok is True
    assert "me.bsky.social" in msg
