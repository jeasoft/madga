# Publishers + Channels

MADGA broadcasts go to publishers. A publisher = one destination type
(X, LinkedIn, email subscribers, …). For each publisher, every Site
connects its own account(s).

## Built-in

| Key | Label | Auth | char limit | Real publish |
|---|---|---|---|---|
| `email_subscribers` | Email subscribers | Django EMAIL_BACKEND | — | ✅ |
| `mastodon` | Mastodon | Access token | 500 | ✅ |
| `bluesky` | Bluesky | App password | 300 | ✅ |
| `twitter` | X (Twitter) | OAuth 2.0 PKCE | 280 | ✅ |
| `linkedin` | LinkedIn | OAuth 2.0 | 3000 | ✅ |
| `instagram` | Instagram | OAuth via Facebook Graph | 2200 | ✅ |

## Custom publishers

Register from `apps.ready()`:

```python
from madga.publishers import Publisher, PublishResult, register_publisher, CredField

@register_publisher
class SlackPublisher(Publisher):
    key = "slack"
    label = "Slack"
    icon = "send"
    char_limit = 4000
    credential_fields = [
        CredField("webhook_url", "Incoming webhook URL", secret=True),
    ]

    def _publish_one(self, job, account):
        import json, urllib.request
        creds = account.get_credentials()
        url = creds["webhook_url"]
        body = json.dumps({"text": job.body_text or job.subject}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
```

## OAuth setup

OAuth-supported publishers (`twitter`, `linkedin`, `instagram`) need
the operator to register a single app per platform in their developer
console, then add credentials to `settings.py`:

```python
MADGA_OAUTH = {
    "twitter":   {"client_id": "...", "client_secret": "..."},
    "linkedin":  {"client_id": "...", "client_secret": "..."},
    "instagram": {"client_id": "...", "client_secret": "..."},
}
```

The studio walks each user through this in `/studio/channels/<key>/oauth/setup/`.

## BYOA — per-Site override

Enterprise tenants can register their own platform app per workspace
so the OAuth consent screen shows their brand. Studio →
`/studio/channels/<key>/byoa/` form. Stored encrypted via the same
Fernet helper as channel tokens.

## SaaS pattern

- ONE platform app per MADGA deployment (in `MADGA_OAUTH`)
- Each tenant connects THEIR OWN social account through it
- Tokens stored per-Site in `PublisherAccount` — isolated by tenant
- This is how Buffer / Hootsuite / Zapier work
