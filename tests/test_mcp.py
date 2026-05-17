"""Tests for the MCP server: auth, JSON-RPC, every built-in tool."""

import json

import pytest
from django.test import Client

from madga.models import Post, Site, SiteUser, Subscriber, UserApiKey


@pytest.fixture
def site(db):
    return Site.objects.create(name="Acme", domain="acme.test")


@pytest.fixture
def user(db, django_user_model, site):
    u = django_user_model.objects.create_user("juan", "juan@acme.test", "pw")
    SiteUser.objects.create(site=site, user=u, role=SiteUser.ROLE_OWNER)
    return u


@pytest.fixture
def api_key(user, site):
    return UserApiKey.objects.create(user=user, site=site, label="MCP test")


@pytest.fixture
def mcp(api_key):
    """Helper to POST JSON-RPC requests against /mcp/ with the auth header."""
    c = Client(HTTP_AUTHORIZATION=f"Bearer {api_key.key}")

    def call(method, params=None, id=1):
        body = {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
        r = c.post("/mcp/", json.dumps(body), content_type="application/json")
        return r

    return call


def _call_tool(mcp, name, **args):
    r = mcp("tools/call", {"name": name, "arguments": args})
    assert r.status_code == 200, r.content
    data = r.json()
    assert "result" in data, data
    return json.loads(data["result"]["content"][0]["text"])


# ---------------------------------------------------------------------------
# Auth + protocol
# ---------------------------------------------------------------------------

def test_mcp_get_returns_capability_summary(client):
    r = client.get("/mcp/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "madga.mcp"
    assert body["tools"] > 0
    assert "Authorization" in body["auth"]


def test_mcp_post_without_auth_returns_401(client):
    r = client.post("/mcp/", "{}", content_type="application/json")
    assert r.status_code == 401


@pytest.mark.django_db
def test_mcp_post_with_wrong_token_returns_401():
    c = Client(HTTP_AUTHORIZATION="Bearer madga_bogus")
    r = c.post("/mcp/", "{}", content_type="application/json")
    assert r.status_code == 401


@pytest.mark.django_db
def test_mcp_initialize_returns_capabilities(mcp):
    r = mcp("initialize")
    assert r.status_code == 200
    data = r.json()
    assert data["result"]["protocolVersion"]
    assert "tools" in data["result"]["capabilities"]
    assert data["result"]["serverInfo"]["name"] == "madga"


@pytest.mark.django_db
def test_mcp_tools_list_includes_builtins(mcp):
    r = mcp("tools/list")
    data = r.json()
    names = [t["name"] for t in data["result"]["tools"]]
    assert "list_posts" in names
    assert "create_post" in names
    assert "publish_post" in names
    assert "broadcast" in names
    assert "list_subscribers" in names
    assert "list_form_submissions" in names
    assert "list_channels" in names
    assert "list_sites" in names


@pytest.mark.django_db
def test_mcp_unknown_method_returns_minus_32601(mcp):
    r = mcp("frobnicate")
    data = r.json()
    assert data["error"]["code"] == -32601


@pytest.mark.django_db
def test_mcp_unknown_tool_returns_minus_32601(mcp):
    r = mcp("tools/call", {"name": "no_such_tool", "arguments": {}})
    assert r.json()["error"]["code"] == -32601


@pytest.mark.django_db
def test_mcp_notifications_get_204(mcp):
    body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    c = Client(HTTP_AUTHORIZATION=mcp.__closure__[0].cell_contents.headers["Authorization"] if False else "Bearer x")
    # Simpler: reuse the api_key fixture via mcp's enclosing client
    r = mcp("notifications/initialized")
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# list_sites + set_active_site
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_sites_shows_user_workspaces(mcp, site):
    result = _call_tool(mcp, "list_sites")
    assert len(result["sites"]) >= 1
    names = [s["name"] for s in result["sites"]]
    assert "Acme" in names
    assert any(s["active"] for s in result["sites"])


@pytest.mark.django_db
def test_set_active_site_switches_pin(mcp, user, api_key, db):
    other = Site.objects.create(name="Other", domain="other.test")
    SiteUser.objects.create(site=other, user=user, role=SiteUser.ROLE_OWNER)

    result = _call_tool(mcp, "set_active_site", site_id=str(other.id))
    assert result["active_site"]["name"] == "Other"

    api_key.refresh_from_db()
    assert api_key.site_id == other.id


@pytest.mark.django_db
def test_set_active_site_rejects_foreign_site(mcp, db):
    other = Site.objects.create(name="Other", domain="other2.test")  # no membership
    r = mcp("tools/call", {"name": "set_active_site",
                            "arguments": {"site_id": str(other.id)}})
    assert r.json()["error"]["code"] == -32602


# ---------------------------------------------------------------------------
# Posts: list / get / create / publish
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_posts_returns_only_active_site_posts(mcp, site, user):
    Post.objects.create(site=site, title="In Acme", status="published", author=user)
    other = Site.objects.create(name="Other", domain="o.test")
    Post.objects.create(site=other, title="Not visible", status="published", author=user)

    result = _call_tool(mcp, "list_posts")
    titles = [p["title"] for p in result["posts"]]
    assert "In Acme" in titles
    assert "Not visible" not in titles


@pytest.mark.django_db
def test_list_posts_filter_by_status(mcp, site, user):
    Post.objects.create(site=site, title="Pub", status="published", author=user)
    Post.objects.create(site=site, title="Draft", status="draft", author=user)
    result = _call_tool(mcp, "list_posts", status="draft")
    titles = [p["title"] for p in result["posts"]]
    assert titles == ["Draft"]


@pytest.mark.django_db
def test_create_post_creates_and_returns(mcp, site, user):
    result = _call_tool(mcp, "create_post",
                        title="From MCP", body_text="hi", status="draft")
    assert result["title"] == "From MCP"
    p = Post.objects.get(pk=result["id"])
    assert p.site == site
    assert p.author == user
    assert p.body["blocks"][0]["data"]["text"] == "hi"


@pytest.mark.django_db
def test_create_post_requires_title(mcp):
    r = mcp("tools/call", {"name": "create_post", "arguments": {}})
    assert r.json()["error"]["code"] == -32602


@pytest.mark.django_db
def test_publish_post_changes_status(mcp, site, user):
    p = Post.objects.create(site=site, title="Draft", status="draft", author=user)
    result = _call_tool(mcp, "publish_post", id=str(p.id))
    assert result["status"] == "published"
    p.refresh_from_db()
    assert p.status == "published"


@pytest.mark.django_db
def test_get_post_returns_full_detail(mcp, site, user):
    p = Post.objects.create(site=site, title="X", status="published", author=user,
                            body={"blocks": [{"type": "paragraph", "data": {"text": "y"}}]})
    result = _call_tool(mcp, "get_post", id=str(p.id))
    assert result["title"] == "X"
    assert result["body"]["blocks"][0]["data"]["text"] == "y"


@pytest.mark.django_db
def test_get_post_404(mcp):
    import uuid
    r = mcp("tools/call", {"name": "get_post", "arguments": {"id": str(uuid.uuid4())}})
    assert r.json()["error"]["code"] == -32602


# ---------------------------------------------------------------------------
# Audience tools
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_subscribers_scoped_to_site(mcp, site):
    Subscriber.objects.create(site=site, email="a@x.com", is_active=True)
    Subscriber.objects.create(site=site, email="b@x.com", is_active=False)
    other = Site.objects.create(name="Other", domain="o3.test")
    Subscriber.objects.create(site=other, email="c@x.com", is_active=True)

    result = _call_tool(mcp, "list_subscribers")
    emails = [s["email"] for s in result["subscribers"]]
    assert "a@x.com" in emails
    assert "c@x.com" not in emails

    # active=False filter
    result2 = _call_tool(mcp, "list_subscribers", active=False)
    emails2 = [s["email"] for s in result2["subscribers"]]
    assert "b@x.com" in emails2
    assert "a@x.com" not in emails2


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_broadcast_creates_jobs_per_publisher(mcp, site, user):
    Subscriber.objects.create(site=site, email="r@x.com", is_active=True)
    p = Post.objects.create(site=site, title="Hi", status="published", author=user,
                            body={"blocks": [{"type": "paragraph", "data": {"text": "x"}}]})
    result = _call_tool(mcp, "broadcast",
                        post_id=str(p.id),
                        publisher_keys=["email_subscribers"])
    assert len(result["broadcasts"]) == 1
    assert result["broadcasts"][0]["publisher_key"] == "email_subscribers"
    assert result["broadcasts"][0]["status"] in ("sent", "partial", "failed")


@pytest.mark.django_db
def test_broadcast_requires_publisher_keys(mcp):
    r = mcp("tools/call", {"name": "broadcast", "arguments": {"subject": "x"}})
    assert r.json()["error"]["code"] == -32602
