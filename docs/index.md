# MADGA docs

MADGA is a CMS that ships as a single Django app. Studio + headless API + public renderer + broadcast/channels + MCP server, all from `pip install madga`.

This doc tree mirrors what's in [`README.md`](../README.md) but split into pages so it's easier to link / search / extend. The `mkdocs-material` site lands in a follow-up release.

## Sections

- [Quickstart](../README.md#quick-start) — the 5-minute install
- [Publishers + Channels](publishers.md) — fan out to X / LinkedIn / Instagram / Mastodon / Bluesky / email
- [Webhooks](webhooks.md) — outbound HTTP events for host projects
- [MCP server](mcp.md) — AI-assistant access via per-user API keys
- [Custom block types](blocks.md) — extend the homepage builder
- [Multi-tenant / SaaS](saas.md) — workspace switcher, BYOA per-Site OAuth apps

## Where to look in code

```
madga/
├── blog/         # public site (homepage, posts, pages, RSS, sitemap)
├── studio/       # the backoffice (/studio/)
├── api/          # Ninja-based headless API (/api/madga/v1/)
├── mcp/          # MCP JSON-RPC server (/mcp/)
├── publishers/   # email + 5 social channels + the registry
├── models/       # Site, Post, Page, Broadcast, Subscriber, Webhook, Channel, etc.
├── templates/    # studio chrome + public blocks + email + error pages
└── locale/       # ES + EN translations (shipped in the wheel)
```
