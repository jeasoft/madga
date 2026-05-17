# Webhooks

MADGA fires HTTP POSTs to URLs you register when things happen
inside the CMS — post published, subscriber added, form submitted,
broadcast finished, etc.

## Events shipped

```
post.published       post.unpublished     post.updated     post.deleted
page.published       page.updated         page.deleted
media.uploaded
subscriber.created   subscriber.unsubscribed
broadcast.sent       broadcast.failed
form.submitted
```

Host projects can append their own to `REGISTERED_EVENTS`.

## Receiver contract

Each delivery is a POST with body:

```json
{
  "id": "<delivery-uuid>",
  "event": "post.published",
  "created_at": "2026-05-17T08:00:00Z",
  "data": { ...event-specific payload... }
}
```

Headers:

- `Content-Type: application/json`
- `X-Madga-Event` — same as `event` in the body
- `X-Madga-Delivery` — unique per attempt
- `X-Madga-Timestamp` — unix seconds
- `X-Madga-Signature` — `t=<unix>,v1=<hex>`

### Verify signatures

Compute `HMAC-SHA256(secret, f"{timestamp}.{body}")` and compare to
the `v1=` chunk. Reject if `timestamp` is too old (replay
protection). Stripe's webhook signing format — same shape.

```python
import hmac, hashlib

def verify(secret: str, headers: dict, body: bytes) -> bool:
    sig = headers["X-Madga-Signature"]
    parts = dict(p.split("=") for p in sig.split(","))
    ts = parts["t"]
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(parts["v1"], expected)
```

## Retry behavior

Failed deliveries retry with exponential backoff:
`60s → 5min → 30min → 2h → 12h`, then mark as `failed`. Max
attempts is `MADGA_WEBHOOK_MAX_RETRIES` (default 5).

The worker is `madga webhook-worker [--loop --interval 30]` —
deploy it as a long-running process or a periodic cron.

## Studio UI

`/studio/webhooks/` — list, create, test (sync POST so you see the
response), rotate secret, pause/resume, delete. Recent deliveries
table with status + retry count.
