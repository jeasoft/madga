# MCP server

MADGA ships an MCP (Model Context Protocol) server at `/mcp/` so any
AI assistant — Claude, Claude Code, custom agents — can drive your
CMS programmatically. Auth uses the same per-user API keys minted in
the studio.

## What an MCP-connected user can do

- *"List the posts I have in draft"* → `list_posts(status="draft")`
- *"Create a draft about Senior Python Dev jobs"* → `create_post(...)`
- *"Publish that"* → `publish_post(id=...)`
- *"Broadcast my latest post to X, LinkedIn, and Instagram"* → `broadcast(post_id=..., publisher_keys=["twitter","linkedin","instagram"])`
- *"Show me unread form submissions from this week"* → `list_form_submissions(unread_only=true)`
- *"Switch to my Acme Corp workspace"* → `set_active_site(site_id=...)`

## Setup

### 1. Mint an API key

In the studio: **API keys → Generate new key**. Copy the value
(starts with `madga_`).

### 2. Configure your MCP client

Any client that speaks MCP over HTTP works. Example for a Claude
desktop / agent that supports HTTP transports:

```json
{
  "mcpServers": {
    "madga": {
      "url": "https://your-madga.com/mcp/",
      "headers": {
        "Authorization": "Bearer madga_YOUR_KEY_HERE"
      }
    }
  }
}
```

For Claude Code (stdio-first), use a small wrapper that proxies stdio
to the HTTP endpoint. The MCP team's `mcp-proxy` package does this:

```bash
pip install mcp-proxy
mcp-proxy https://your-madga.com/mcp/ \
  --header "Authorization: Bearer madga_YOUR_KEY"
```

## Tools shipped

| Tool | What it does |
|---|---|
| `list_sites` | Workspaces the user can access |
| `set_active_site` | Switch which workspace tools operate on (persisted on the key) |
| `list_posts` | Posts in the active site (filter by status, search, limit) |
| `get_post` | Full detail including body JSON + body_html |
| `create_post` | Create a draft / published post |
| `publish_post` | Set a post to status=published |
| `list_pages` | Static pages |
| `list_subscribers` | Email subscribers (filter by active, search) |
| `list_form_submissions` | Inbox entries (filter by form_key, unread) |
| `list_channels` | Connected social/email channels per site |
| `list_broadcasts` | Broadcast job history |
| `broadcast` | Fan out a post (or standalone message) to one or more publishers |

## Adding your own tools

Same pattern as block types and publishers — register from the host
project's `apps.ready()`:

```python
# myapp/mcp_tools.py
from madga.mcp import register_tool, ToolError

@register_tool(
    name="apply_to_job",
    description="Create a job Application from the active user's profile to a Post.",
    input_schema={
        "type": "object",
        "properties": {"post_id": {"type": "string"}},
        "required": ["post_id"],
    },
)
def apply_to_job(ctx, post_id=None, **_):
    if not post_id:
        raise ToolError("post_id required")
    # ctx.user is the authenticated user, ctx.site is their active Site
    from aplica_do.models import Application
    app = Application.objects.create(user=ctx.user, post_id=post_id)
    return {"application_id": str(app.id)}
```

## Protocol details

- Transport: HTTP JSON-RPC 2.0
- POST body is a single request or a batch (list)
- Methods: `initialize`, `tools/list`, `tools/call`, `ping`
- Errors follow JSON-RPC: `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32603` internal error
- A GET on `/mcp/` returns a tiny capability summary for sanity checks

## Site isolation

Every tool scopes its queries by `ctx.site` (the user's active
workspace). Cross-tenant access is impossible by construction — even
a tool that calls `Post.objects.all()` would only return the active
site's rows because of the publisher-level filtering and the site
membership check that gates `ctx.site` itself.
