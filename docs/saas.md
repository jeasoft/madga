# Multi-tenant / SaaS

MADGA is multi-tenant by design. Most things scope to `Site` (the
tenant primitive) automatically — every queryset that returns
post / page / subscriber / broadcast / channel / webhook /
submission rows filters by `site=` first.

## The Site model

One row per tenant. Has its own name, domain, theme tokens, OAuth
app overrides, GA / Pixel IDs, etc.

## SiteUser membership

`User × Site → role (owner / editor / author / contributor)`. A user
can belong to multiple sites. The active site is resolved by:

1. Pre-set `request.madga_site` (host project mounts MADGA under
   `/company/<slug>/studio/` and resolves slug → Site before
   MADGA's middleware fires)
2. Session pin (workspace switcher)
3. Host header
4. First active site (fallback)

## Workspace switcher

Sidebar dropdown. Lists every Site the user belongs to. POSTs to
`/studio/workspaces/switch/`. Persists on the user session so
subsequent requests remember.

## Self-service workspace create

`/studio/workspaces/new/` — any authenticated user can spin up a new
Site, becomes its owner, gets dropped into it.

## OAuth in a SaaS

Standard model (Buffer / Hootsuite / Zapier):

```
SaaS operator (aplica.do)
└── settings.py MADGA_OAUTH = {...}  ← ONE platform app
    │
    ├── Tenant A connects THEIR social account → token stored per Site
    ├── Tenant B connects THEIR social account → token stored per Site
    └── ...
```

When tenant A clicks Connect on Channels, they go through OAuth
with the *operator's* platform app, but log in with *their own*
social account. The consent screen says "aplica.do wants access
to your Instagram (@tenantA)".

### BYOA — Bring Your Own App

Enterprise tenants can override `MADGA_OAUTH` with their own
client_id/secret per workspace. `/studio/channels/<key>/byoa/`.
Then the consent screen shows *their* brand instead of the
operator's. Token storage is unchanged.

## Site isolation audit

Every studio view goes through `MadgaStudioMiddleware` which sets
`request.madga_site` to the active site. Tools layered on top
(broadcasts, channels, webhooks, MCP) all filter querysets by
`site=request.madga_site` (or its MCP equivalent
`ctx.site`). Cross-tenant data leaks would require a bug in
exactly those filters — not a structural deficiency.

## Custom domains

DNS layer — host project's concern. Point each tenant's domain at
the same MADGA instance, set `Site.domain` to match, and the
host-header resolution path picks the right Site automatically.
