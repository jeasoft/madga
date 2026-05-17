# CHANGELOG

All notable changes to MADGA. Format roughly follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4.0] — 2026-05-17

Focus: **MCP server + docs/ skeleton.** MADGA is now AI-native — any
Claude / agent that speaks MCP can drive the studio (read posts,
create posts, publish, broadcast to channels, view subscribers and
the form inbox) using a per-user API key.

### Added — MCP server
- **`madga.mcp` module** + HTTP transport at ``/mcp/``. Minimal
  JSON-RPC 2.0 dispatcher (initialize / tools/list / tools/call /
  ping / notifications) — sync Django views, no extra deps, no
  ASGI required.
- **Auth via existing UserApiKey** (``Bearer madga_<token>``). The
  key's pinned ``site`` field doubles as the MCP active-workspace
  state; the ``set_active_site`` tool updates it.
- **Tools shipped (12 total)**:
  - Sites: ``list_sites``, ``set_active_site``
  - Content: ``list_posts``, ``get_post``, ``create_post``,
    ``publish_post``, ``list_pages``
  - Audience: ``list_subscribers``, ``list_form_submissions``
  - Channels: ``list_channels``, ``list_broadcasts``, ``broadcast``
- **Host-project extensibility**: ``@register_tool`` decorator with
  the same pattern as ``@register_block_type`` / ``@register_publisher``.
- **Site isolation**: every tool filters by ``ctx.site`` — cross-tenant
  reads/writes are impossible by construction.
- **GET /mcp/** returns a tiny capability summary so devs can verify
  the endpoint is mounted without writing a JSON-RPC client.
- 21 new tests covering protocol, auth, every built-in tool path
  (happy + error paths). **142 total green on sqlite + Postgres.**

### Added — docs skeleton
- **`docs/`** folder with hand-written markdown:
  - ``index.md`` — overview + section pointers
  - ``mcp.md`` — full MCP guide with setup + tool reference
  - ``publishers.md`` — built-in publishers + custom publisher recipe
  - ``webhooks.md`` — events catalog + receiver contract + signature verification snippet
  - ``saas.md`` — multi-tenant model + workspace switcher + BYOA
  - ``blocks.md`` — custom block types
- ``mkdocs-material`` site lands in 0.4.1 (markdown is enough for
  now — GitHub renders it inline).

## [0.3.9] — 2026-05-17

Focus: **BYOA (Bring Your Own App)** — per-Site OAuth app credential
overrides. Most tenants will use the operator's shared app; enterprise
tenants can register their own platform app per workspace so the
OAuth consent screen shows their brand.

### Added
- **`SiteOAuthApp` model** (per-Site × publisher_key, unique). Stores
  ``client_id`` + Fernet-encrypted ``client_secret`` + optional notes.
- **`Publisher.oauth_client_credentials(site=...)`** resolves in this
  order: per-Site override → ``MADGA_OAUTH`` settings → ``None``.
  Every OAuth call site (start, callback, setup view, exchange,
  authorize URL) now passes the active site, so each tenant gets
  their override (or the shared default).
- **`/studio/channels/<key>/byoa/`** — per-publisher form to paste
  client_id + client_secret + notes. Empty client_id reverts to the
  shared app. Empty client_secret on edit keeps the stored value
  (so the user can tweak notes without re-pasting the secret).
- **Channels page UX**:
  - "Use my own" button on every "Needs setup" card → BYOA form
  - "Use my own app instead →" hint under each Connect button
  - "Using custom app · edit" link when an override is active
- 10 new tests covering encryption round-trip, override precedence,
  view CRUD, channels-page state. **121 total green.**

### Migration notes
- New migration ``0014_byoa``. Run ``python manage.py migrate``.
- Existing connected accounts (PublisherAccount rows) are unaffected.
  BYOA only changes the **app** credentials used during the OAuth
  flow, not the **user tokens** that come out of it.

## [0.3.8] — 2026-05-17

Focus: **Instagram via Facebook Graph.** Closes the loop on the
five major social channels — every publisher MADGA ships now has
a real, working ``publish()``.

### Added
- **`InstagramOAuthPublisher`** with full OAuth + two-step Graph
  API publishing. The OAuth dance: Facebook Login → user grants
  scopes (instagram_basic, instagram_content_publish,
  pages_show_list, pages_read_engagement, business_management)
  → exchange short-lived for long-lived user token → list Pages
  the user admins → pick the first Page with an Instagram
  Business Account attached → store everything as the
  PublisherAccount's credentials.
- **Two-step publish**: POST ``/{ig_user_id}/media`` with
  ``image_url`` + caption → returns ``creation_id`` (media
  container). POST ``/{ig_user_id}/media_publish`` with
  ``creation_id`` → publishes. The publisher derives the image
  URL from the post's ``featured_image`` (or ``og_image``)
  with the site's domain prepended.
- **Hard fail with clear message** if (a) no featured image is
  set or (b) the resolved URL is localhost (Meta fetches the URL
  from its own servers, so dev needs ngrok). No more silent
  failures buried in API responses.
- **`test_connection()`** hits ``/{ig_user_id}?fields=username,
  followers_count`` and surfaces both in the studio message.
- **Setup guide** for Instagram covering the IG Business
  Account → Facebook Page link (a prerequisite people miss),
  required FB app products + scopes, Live mode for non-admin
  users.

### Tests
- 7 new tests (HTTP mocked end-to-end) — full OAuth callback
  walkthrough + two-step publish + failure paths for
  missing-image and localhost-url. 111 total.

### Five-publisher checkpoint
- Mastodon ✅ (token, no OAuth needed)
- Bluesky ✅ (app password, no OAuth)
- X (Twitter) ✅ (OAuth 2.0 PKCE)
- LinkedIn ✅ (OAuth 2.0)
- Instagram ✅ (OAuth via Facebook Graph)
- + Email subscribers ✅ (built-in)

Next: 0.4.0 = MCP server (exposes all of this to Claude) + docs site.

## [0.3.7] — 2026-05-17

Focus: **integration surface.** OAuth setup guides, outbound
webhooks, and public form blocks. With this release, aplica.do
(or any host project) has every primitive it needs to integrate
MADGA into a real product: connect channels with help, get
notified when things happen, accept submissions from visitors.

### Added — OAuth setup UX
- **Per-platform setup guide.** Each OAuth Publisher declares
  ``setup_instructions`` (a list of {title, body, url} steps with
  ``<copy>...</copy>`` chunks promoted to copy-paste boxes) and
  ``setup_console_url``. The new ``/studio/channels/<key>/oauth/setup/``
  page renders these with the actual callback URL substituted, plus
  the link to the platform's developer console.
- **Setup guide button** on the "Needs setup" card on the Channels
  page replaces the bare "Add MADGA_OAUTH..." hint — one click into
  the step-by-step walk-through.

### Added — Outbound webhooks
- **`WebhookEndpoint` + `WebhookDelivery` models** per Site, with
  HMAC-SHA256 signing using a per-endpoint random secret. Signature
  format follows Stripe's: ``t=<unix>,v1=<hex>``.
- **`madga.webhooks.fire_event(site, event, payload)`** — what
  application code (or our signal handlers) calls. Looks up matching
  endpoints, creates pending delivery rows. Never raises.
- **`madga.webhooks.deliver_pending(limit, dry_run)`** — what the
  worker drives. Exponential-backoff retry (60s / 5m / 30m / 2h /
  12h), gives up after ``MADGA_WEBHOOK_MAX_RETRIES`` (default 5).
- **Signal-fired events shipped:** ``post.published``,
  ``post.unpublished``, ``post.updated``, ``page.updated``,
  ``page.published``, ``media.uploaded``, ``broadcast.sent``,
  ``broadcast.failed``, ``subscriber.created``,
  ``subscriber.unsubscribed``, ``form.submitted``. Catalog in
  ``REGISTERED_EVENTS`` — host projects can append their own.
- **Studio UI** at ``/studio/webhooks/``: list endpoints, recent
  deliveries log with retry counts, per-endpoint Test button (sync
  POST so you see the response immediately), rotate-secret action,
  pause/resume, delete.
- **`madga webhook-worker`** management subcommand. ``--loop`` mode
  for production deploys, ``--dry-run`` for CI.

### Added — Form blocks
- **New ``ContactFormBlock``** in the block registry — drop it on a
  homepage or in a Post body. Settings: title, subtitle, button
  label, success message, recipient email, form key. Public
  template renders name + email + message inputs + a honeypot
  (silently drops bots).
- **`FormSubmission` model** + public POST endpoint
  ``/madga/form/<block_id>/submit/`` that creates a row, optionally
  emails the recipient, and fires a ``form.submitted`` webhook.
  Accepts both regular form posts (redirects with
  ``?submitted=<id>``) and JSON (returns ``{ok: true, id}``).
- **Studio inbox** at ``/studio/inbox/``: search, filter by form
  key, mark read/unread, CSV export.

### Tests
- 17 new tests for webhooks + forms. 104 total.

### Pending for 0.3.8 / 0.4.0
- Instagram via Facebook Graph (deferred).
- 0.4.0: **MCP server** + docs site.

## [0.3.6.1] — 2026-05-16

### Added
- Channels page shows a **"Needs setup"** hint card on OAuth
  publishers whose ``MADGA_OAUTH['<key>']`` config isn't set,
  with the exact settings dict path. Previously the user had to
  click Connect and read the error toast — now the gap is visible
  upfront.

## [0.3.6] — 2026-05-16

Focus: **real OAuth for X (Twitter) + LinkedIn.** Click Connect →
walk through the platform's consent UI → click Send broadcast and
the post actually shows up in your feed.

### Added
- **OAuth abstraction in `Publisher` base.** New ``oauth_supported``
  attribute, ``oauth_scopes`` list, ``oauth_client_credentials()``
  reader, ``oauth_authorize_url(...)`` + ``oauth_exchange(...)`` hooks.
- **`MADGA_OAUTH` settings dict.** Host projects register their
  platform apps once::

      MADGA_OAUTH = {
          "twitter":  {"client_id": "...", "client_secret": "..."},
          "linkedin": {"client_id": "...", "client_secret": "..."},
      }

  Per-Site user tokens are stored in `PublisherAccount` rows
  (encrypted by 0.3.4's Fernet helper).
- **`/studio/channels/<key>/oauth/start/`** — generates PKCE
  verifier + state, stores them in session, redirects to the
  platform's authorize URL.
- **`/studio/channels/<key>/oauth/callback/`** — validates state,
  exchanges code for tokens, looks up the user, creates the
  PublisherAccount, flashes success.
- **Real `TwitterOAuthPublisher`** (in `madga/publishers/twitter.py`)
  — OAuth 2.0 PKCE flow, calls `/2/users/me` after token exchange
  to grab the username for display, posts via `/2/tweets`. Replaces
  the old stub.
- **Real `LinkedInOAuthPublisher`** (in `madga/publishers/linkedin.py`)
  — OAuth 2.0 standard flow, fetches `/v2/userinfo` to grab the
  person URN needed to author posts, publishes via `/v2/ugcPosts`.
  Replaces the old stub.
- **Connect button dispatcher.** Existing `/connect/` URL now
  redirects to the OAuth start view automatically for
  `oauth_supported` publishers — manual flow stays for Mastodon,
  Bluesky, Instagram.
- 8 new tests for the OAuth flow + Twitter/LinkedIn publish
  paths (HTTP calls mocked). 86 total.

### Fixed
- `Publisher.is_configured(site)` now also requires an active
  ``PublisherAccount`` for OAuth-supported publishers (previously
  it returned True for them because their `credential_fields` is
  empty — they'd show as configured before being connected).

### Migration notes
- Already-connected Twitter accounts created against the 0.3.4
  stub will not survive — the stored credentials no longer match
  the publisher's expected shape. Disconnect + reconnect via OAuth.
  LinkedIn stub accounts had the same shape change.

### Pending for 0.3.7
- Instagram via Facebook Graph (two-step container + publish flow,
  much more complex than Twitter/LinkedIn).
- Outbound webhooks for host projects to subscribe to MADGA events.
- Form blocks (contact form / lead capture + studio inbox).

## [0.3.5] — 2026-05-16

Focus: **real publishers for the easy platforms + auto-broadcast.**
Mastodon and Bluesky now actually post when the broadcast worker
fires; X / LinkedIn / Instagram remain stubs (their OAuth flows land
in 0.3.6). Posts can now schedule broadcasts that fire automatically
when the post transitions to published.

### Added
- **Real `MastodonPublisher.publish()`** — POSTs to
  `{instance_url}/api/v1/statuses` with the stored access token,
  visibility=public. Also a real `test_connection()` that hits
  `/api/v1/accounts/verify_credentials` and returns the verified
  username. Works against any Mastodon instance (hachyderm.io,
  mastodon.social, self-hosted, …).
- **Real `BlueskyPublisher.publish()`** — `createSession` with
  handle + app_password to get an `accessJwt`, then `createRecord`
  to post an `app.bsky.feed.post`. No OAuth dance needed; the app
  password the user generates under Bluesky → Settings → App Passwords
  is the only secret. Includes real `test_connection()` that
  authenticates and returns the resolved DID.
- **`BroadcastJob.STATUS_QUEUED_ON_PUBLISH`** state + signal
  handler. The drawer now offers "When this post publishes" as a
  schedule mode for draft posts; the rows sit in
  `queued_on_publish` until `Post.status` transitions to `published`,
  at which point the post-save signal flips them to `pending` and
  runs them through the same `_worker_run` pipeline as immediate
  broadcasts.
- **Broadcast button works on drafts.** Previously the studio post
  editor only showed the Broadcast button after publishing. Now it
  shows on drafts too — the drawer defaults to "When this post
  publishes" so editors can set up their fan-out before hitting
  Publish.
- **`_AccountPublisher` base class** that handles per-account
  fan-out, error capture, and `last_used_at` / `last_error` updates.
  Subclasses just override `_publish_one(job, account)`. Old name
  `_AccountStubPublisher` kept as an alias for back-compat with
  any host project that subclassed it.
- 7 new tests (78 total). The Mastodon and Bluesky tests patch the
  HTTP helper so they don't need real network access in CI.

### Fixed (audit pass)
- 3 hardcoded Spanish ``PermissionDenied`` messages in `posts.py`
  (``"No podés editar este post."`` etc.) wrapped in `_()`.
- 6 hardcoded Spanish ``messages.success``/``warning`` calls
  across `users.py`, `pages.py`, `homepage.py`.
- ``NavItem.LOCATION_CHOICES`` labels (`"Header"`/`"Footer"`)
  wrapped in `gettext_lazy`.
- ``"Sin título"`` fallback in `context_processors.py` + `preview.py`
  switched to `_("Untitled")`.
- Spanish placeholder text in `blocks/fields.py` (UrlField widget)
  translated to English.

## [0.3.4.2] — 2026-05-16

### Fixed
- **Duplicate "Handle" field in the channel Connect form.** Bluesky
  declares ``handle`` as part of its credential schema (the bsky.social
  handle is the auth identity), so the form rendered both that input
  AND the generic studio-level Handle input — confusing and they
  fought over the same POST key. The studio handle is now suppressed
  when the publisher already has a ``handle`` credential field, and
  the value gets reused as the display label.
- Added ``Publisher.has_handle_credential`` property to drive the
  conditional.

## [0.3.4.1] — 2026-05-16

Hot-fix on top of 0.3.4.

### Fixed
- **Raw template comment leaking into the public homepage.**
  ``tracking.html`` had a multi-line ``{# ... #}`` Django comment;
  Django comments are single-line only, so the whole comment block
  rendered as visible text above the site header. Same issue was
  hiding in the broadcast drawer and signup templates. Fixed by
  switching to ``{% comment %}…{% endcomment %}`` everywhere.

### Added
- **Test connection button** on every connected channel card. Calls
  ``Publisher.test_connection(account)``:
  - For account-driven stubs (X, Mastodon, Bluesky, LinkedIn,
    Instagram): verifies the credential fields are populated. Real
    API verification lands in 0.3.5.
  - For the email publisher: actually opens the configured
    ``EMAIL_BACKEND`` (real SMTP for smtp backends, no-op for
    console). Surfaces the error otherwise.
  Result is flashed back, and the account row keeps the failure
  message in ``last_error`` so it's visible on the page.
- 4 new tests for ``test_connection`` paths.

## [0.3.4] — 2026-05-16

Focus: **Channels + SaaS foundations.** MADGA can now host multiple
companies/tenants and broadcast to each one's own social channels.

### Added — SaaS plumbing
- **Multi-site middleware respects pre-set `request.madga_site`.**
  Host projects can resolve the active Site from URL/path (e.g.
  `aplica.do/company/<slug>/...`) before MADGA's middleware fires and
  it won't overwrite the choice. Order: pre-set → session pin →
  host-header → first active.
- **Workspace switcher (functional).** Sidebar dropdown lists every
  Site the user belongs to, POSTs to `/studio/workspaces/switch/`,
  pins the choice in session, redirects. Superusers see every active
  Site. Stale session pins (memberships revoked) are dropped
  automatically.
- **Self-service `/studio/workspaces/new/`.** Any authenticated user
  can spin up a new Site, becomes its Owner, gets dropped into it.
  No CLI admin required.

### Added — Channels
- **`PublisherAccount` model** (one row per `Site × publisher × handle`)
  with Fernet-encrypted credentials. Pause/resume per account.
- **`madga.encryption`** helper: Fernet key derived from
  `MADGA_CREDENTIAL_KEY` (or list `MADGA_CREDENTIAL_KEYS` for rotation),
  falls back to a `SECRET_KEY`-derived key in dev.
- **Publisher base extended** with `credential_fields` (declarative
  field spec for the Connect form), `char_limit` (drives the per-channel
  composer's counter), and `default_copy(job)` (auto-generates
  per-platform copy trimmed to char limit).
- **Stub publishers shipped:** `TwitterPublisher`, `MastodonPublisher`,
  `BlueskyPublisher`, `LinkedInPublisher`, `InstagramPublisher`. Each
  has credentials schema, char limit, and a stub `publish()` that
  records a clear "not implemented yet" error. Real OAuth + API
  integration lands in 0.3.5.
- **`/studio/channels/`** — stats cards (connected / broadcasts this
  week / total reach / in queue) + grid of every account-driven
  publisher with its connected accounts (pause, edit credentials,
  disconnect).
- **`/studio/channels/<key>/connect/`** — manual token-paste flow
  rendering each publisher's `credential_fields` as inputs (secret
  ones as password). Stores credentials encrypted, surfaces as
  Active immediately.
- **`is_configured(site=None)`** on Publisher: account-driven
  publishers return `True` only when the Site has at least one active
  `PublisherAccount`. The drawer and lists filter by this.

### Added — Per-channel composer
- **Broadcast drawer** rewritten with a two-pane layout: left rail of
  channel pickers (checkbox per registered publisher), right pane with
  per-channel textarea + character counter (turns red over limit).
- **Auto-generated copy** built client-side from post title +
  excerpt + URL, trimmed to each channel's limit (so X gets 280
  chars + URL, LinkedIn gets the full thing, etc.).
- **Schedule modes**: Post immediately / At a specific time. The
  datetime input only enables when "specific time" is selected.
- **Featured image preview** + link card preview render in each pane
  when the post has them.

### Added — Misc
- `cryptography>=42` added as a runtime dependency.
- 16 new tests for channels + encryption + workspace flows. 67 total.

### Migration notes
- New migration `0010_publisheraccount`. Run `python manage.py migrate`.
- **Production:** set `MADGA_CREDENTIAL_KEY` to a dedicated 32-byte
  url-safe base64 Fernet key. Generate with
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Do not rely on the SECRET_KEY fallback in production — if SECRET_KEY
  ever rotates, every stored credential decrypts to garbage.

## [0.3.3] — 2026-05-16

Focus: **production hardening.** What you'd want in place before pointing
a real domain at a MADGA-powered site.

### Added
- **Branded error pages.** Ships `templates/400.html`, `403.html`,
  `404.html`, and `500.html` at the project root so Django picks them
  up without any wiring. 404/403/400 extend `madga/site_base.html`
  (so they inherit your theme); 500 is a self-contained dark page
  (because in 500 land we can't assume any context processor or query
  works).
- **`SecurityHeadersMiddleware`** at `madga.security.SecurityHeadersMiddleware`.
  Sets `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
  `Permissions-Policy`, `Strict-Transport-Security` (on HTTPS),
  `Cross-Origin-Opener-Policy`. CSP is opt-in via `MADGA_CSP` setting
  (CSP is too app-specific to guess). NO-OP in `DEBUG` unless
  `MADGA_SECURITY_FORCE = True`.
- **Cookie consent banner.** New `{% madga_cookie_banner %}`
  template tag, auto-injected from `madga/blog/base.html`. Shows only
  when (a) the Site has at least one tracker configured (GA4 or Meta
  Pixel) AND (b) the visitor hasn't accepted or declined yet. Writes
  `madga_consent` cookie (1y) on click, reloads on accept so the
  trackers can fire.
- **Trackers respect consent.** `madga_tracking` tag now checks the
  `madga_consent` cookie; GA4 + Meta Pixel are gated behind explicit
  opt-in. No tracking fires until the visitor accepts. GDPR-friendly
  default for free.
- **Image optimization on upload.** New `MediaFile.variants` JSONField
  + `imageopt.py` Pillow-driven worker generates `sm/md/lg/xl` WebP
  variants from every image upload. `MediaFile.srcset()` returns a
  ready-to-use `srcset` value. Best-effort: silent fallback to the
  original on failure.
- **Standalone "New broadcast"** button on `/studio/broadcasts/` —
  send an announcement not tied to any post (drawer with subject +
  message body + publisher checkboxes + optional schedule).
- 12 new tests for hardening (51 total).

### Fixed
- `MediaFile.TYPE_CHOICES` had Spanish display labels hardcoded.
  Wrapped in `gettext_lazy`.

### Migration notes
- New migration `0009_mediafile_variants_alter_mediafile_file_type`.
- To enable the security headers, add
  `'madga.security.SecurityHeadersMiddleware'` to `MIDDLEWARE` after
  `'django.middleware.security.SecurityMiddleware'`.

## [0.3.2] — 2026-05-16

Focus: **publisher fan-out.** When you publish a post, MADGA can now
broadcast it to multiple destinations — email subscribers out of the
box, anything you register on top (LinkedIn, Twitter, Facebook, custom
webhook) for host projects like aplica.do that need to publish to
multiple networks in one shot.

### Added
- **`Subscriber` + `BroadcastJob` models** with migrations.
  Subscribers are per-site with unsubscribe tokens; BroadcastJobs are
  frozen-snapshot fan-out records (one job per `publisher × content`
  combination, so retrying or auditing per network works).
- **Publisher registry** under `madga.publishers`. Host projects
  register their own via `@register_publisher`:
  ```python
  @register_publisher
  class LinkedInPublisher(Publisher):
      key = "linkedin"
      label = "LinkedIn"
      def is_configured(self): return bool(settings.LI_TOKEN)
      def publish(self, job): ...  # call LinkedIn API, return PublishResult
  ```
- **Built-in `email_subscribers` publisher** that fans out via Django's
  `EmailMultiAlternatives` (uses `DEFAULT_FROM_EMAIL`). Includes
  RFC 8058 `List-Unsubscribe` one-click headers, HTML + text bodies,
  branded email template that picks up `Site.accent_color`.
- **Studio drawer** on `/studio/posts/<pk>/edit/`. When the post is
  published, a "Broadcast" button slides a drawer with publisher
  checkboxes, subject override, and optional schedule. Sync send for
  immediate jobs; scheduled jobs wait for the worker.
- **`/studio/broadcasts/`** lists all jobs with status, sent/failed
  counts, retry + cancel actions, paginated.
- **`/studio/subscribers/`** manages the audience: add manually,
  search, see active vs. unsubscribed, delete.
- **`/madga/unsubscribe/<token>/`** public one-click endpoint with a
  branded confirmation page that extends `madga/site_base.html`.
- **`madga broadcast-worker`** management subcommand: `--loop` mode
  for production deployments, single-pass by default. Drains pending
  jobs whose `scheduled_at` is past.
- **`madga publishers`** subcommand: lists all registered publishers
  and their `is_configured()` state — useful for debugging missing
  credentials.
- 10 new integration tests for the broadcast flow (email send,
  unsubscribe view, status transitions, studio create endpoint).

### Fixed
- `Post.STATUS_CHOICES`, `Page.STATUS_CHOICES`, `SiteUser.ROLE_CHOICES`,
  and `UserInvitation.STATUS_CHOICES` had display labels hardcoded in
  Spanish. The badges and status dropdowns leaked Spanish into EN
  mode. Wrapped in `gettext_lazy`. Migration `0007` updates the
  choices on Post + Page.

### Migration notes
- Two new migrations: `0007_alter_page_status_alter_post_status` and
  `0008_broadcastjob_subscriber`. Run `python manage.py migrate`.
- If you mount MADGA via the older `include('madga.blog.urls_root')`
  instead of `madga_public_urls()`, the `madga_unsubscribe` route is
  appended automatically — no urls.py changes needed.

## [0.3.1] — 2026-05-16

Bugfix and polish release. Mainly i18n correctness, README, and the publishing toolchain.

### Fixed
- **Dashboard rendered Spanglish.** The `/studio/dashboard/` view had ~20
  hardcoded strings (mixed Spanish/English) and the activity feed
  concatenated `"hace " + timesince` to produce strings like
  `hace 1 week`. Wrapped everything in `{% trans %}` / `{% blocktrans %}`,
  switched relative-time to `humanize`'s `naturaltime`, and added
  `django.contrib.humanize` to `INSTALLED_APPS`. The greeting
  (`_("Good morning")` etc.) now picks up the active language.
- **Studio i18n audit.** Roughly 200 hardcoded user-facing strings
  across post list/edit, page list/edit, media library, theme +
  theme gallery, layouts, navigation, homepage builder, taxonomy,
  users, settings, api keys, login, accept_invite, preview, and
  the topbar were wrapped in translation tags. Source language is
  English; ES translations populated. Legacy Spanish-source view
  messages got English translations in `madga/locale/en/` so EN
  mode no longer leaks Spanish snippets.
- The public `site` template variable is now also available as
  `madga_site` (allauth and other 3rd-party views overwrite `site`).

### Added
- **`madga/locale/` ships with the wheel.** Moved from project-level
  `./locale/` so translations travel with `pip install madga`.
  `pyproject.toml` `package-data` includes `.po` and `.mo` files.
- **GitHub Releases workflow.** `publish.yml` extended with
  `softprops/action-gh-release@v2`: on `v*` tag push, after PyPI
  publish, automatically creates a GitHub Release whose body is
  the matching `CHANGELOG.md` section and whose assets are the
  built sdist + wheel.
- **README polish.** Lead with a hook, screenshot slot, badges,
  reorganized sections. New "Why MADGA" header, condensed quick
  start, and a "Custom signup profiles" section documenting the
  `user_post_signup` signal flow.
- **`docs/screenshots/`** placeholder directory for marketing assets
  referenced from README and the future docs site.

### Migration notes
- If you were importing translations from a project-level
  `./locale/`, MADGA's strings now live in `madga/locale/`. Django
  auto-discovers app locale directories — no settings change needed
  unless you had `LOCALE_PATHS` pinned to the old layout.

## [0.3.0] — 2026-05-16

Focus: **foundation for non-blog projects.** MADGA stops being just a blog CMS and becomes a usable base layer for marketplaces, job boards, and other multi-role products.

### Added
- **`madga/site_base.html`** — thin template that host projects extend
  for any non-blog page (signup, profile, marketplace listings…). Pulls
  the public header/footer chrome, exposes the same `title`,
  `meta_description`, `og`, `head_extra`, `content`, `footer`,
  `body_extra` blocks as the blog templates.
- **Per-user API keys.** `UserApiKey` model with `madga_`-prefixed keys,
  masked display, rotation, last-used tracking. New `/studio/api-keys/`
  page (create / rotate / revoke / delete). `APIKeyAuth` now tries the
  user keys first, falls back to the Site key. `request.user` is set
  when a user key matches.
- **`user_post_signup` custom signal** + bridge from allauth's
  `user_signed_up`. Host projects subscribe to create their profile rows
  (e.g. `TalentProfile`, `CompanyProfile`). Multi-type onboarding
  supported: write `request.session["madga_signup_kind"] = "talent"`
  before signup and the signal receives `kind="talent"`.
- **`madga backfill-profiles --kind=X`** subcommand: re-fires
  `user_post_signup` for every existing User so new profile-extension
  receivers can populate rows retroactively.
- **Public allauth signup wired** with MADGA chrome. Templates
  `account/signup.html` and `account/login.html` extend `site_base.html`
  with i18n strings and styled form widgets.
- **`madga_site` context variable** alongside `site` — survives
  third-party views (allauth, custom views) that overwrite `site` in
  their `get_context_data`. MADGA template tags resolve through this
  to avoid mistaking `django.contrib.sites.Site` for MADGA's Site.
- **Postgres 16 verified.** New `testproject/settings_pg.py` swap-in
  settings; full test suite runs green on both sqlite and Postgres.
  README documents the verify procedure.
- **CI + Publish workflows.** `.github/workflows/ci.yml` runs the suite
  against sqlite + Postgres on every push/PR.
  `.github/workflows/publish.yml` publishes to PyPI on `v*` tags via
  Trusted Publishing (OIDC, no stored secrets).
- 4 new tests for the public signup signal flow.

### Fixed
- Public account templates no longer crash with `VariableDoesNotExist`
  when allauth injects its own `django.contrib.sites.Site` into context
  — `{% firstof %}` in the public base template and template tags fetch
  from `madga_site`.

### Migration notes
- Move `'madga'` BEFORE `'allauth'` in `INSTALLED_APPS` so MADGA's
  `account/signup.html` and `account/login.html` win template
  resolution.
- New migration `0006_userapikey`. Run `python manage.py migrate`.

## [0.2.0] — 2026-05-10

Focus: usable as a library in OTHER projects (not just miscore).

### Added
- **Real packaging.** `pyproject.toml` gains `[build-system]`,
  `[tool.setuptools.packages.find]`, `[tool.setuptools.package-data]` so
  templates, static, migrations, emails ship via pip. `MANIFEST.in` mirrors
  the resource list as a safety net. Verified end-to-end: `pip install
  madga` in a fresh venv + `migrate` + `runserver` → studio loads at 200.
- **Single `madga` CLI** consolidating the previous management commands.
  Subcommands: `create-site`, `seed-demo`, `build-css`, `blocks`, `version`.
  The old standalone `madga_create_site`, `madga_seed`, `madga_tailwind`
  files were removed.
- **First-run welcome page** at `/` when no Site exists. Shows the
  bootstrap commands (createsuperuser + `madga create-site`) instead of
  crashing with a NoneType error on a clean install.
- **Layouts page** functional. Selector per content-type (Homepage / Blog
  index / Post detail / Static pages) with options persisted in
  `Site.settings`. Public template chain prefers `<kind>-<layout>.html`
  when set.
- **Drag-and-drop reorder** for homepage blocks. Sortable.js loaded once
  in `studio/base.html`; any `[data-madga-sortable]` container with a
  `data-reorder-url` becomes draggable. Server-side: a single
  `action=reorder` branch persists `sort_order=index+1` in a transaction.
- **Role enforcement per action.** `MadgaStudioMixin.can_edit_post()` and
  `can_delete_post()`. Author can edit/delete own posts; Editor + Owner
  can edit/delete anyone. Publish silently downgrades to draft when the
  user lacks `publish_post`. Bulk actions filter by permission and warn
  if items were skipped.
- 6 new role-matrix tests; integration suite at 22 tests, all passing.

### Fixed
- `post_edit.html` SERP preview accessed `post.meta_title` /
  `post.title` / `post.excerpt` unguarded, crashing
  `/studio/posts/new/` with `VariableDoesNotExist`. Wrapped in
  `{% if post %}`.

## [0.1.1] — 2026-05-09

### Added
- `Page.featured_image` and `Page.og_image` (FK to MediaFile). New fields
  exposed in `PageForm` and the page editor's right rail.
- `madga.urls.madga_public_urls()` helper consolidates the standard public
  URL patterns (`/`, `/blog/`, `/blog/<slug>/`, `/p/<slug>/`, `/robots.txt`,
  `/sitemap.xml`, `/rss.xml`). Pass `include_homepage=False` if your project
  owns `/`.
- `AcceptInviteView` at `/studio/accept-invite/<token>/`. GET shows
  accept-or-cancel; POST creates `SiteUser` membership + the user account
  if needed. 14-day TTL; expired invitations flip to `status=expired` with
  a friendly UI.
- `madga.studio.invitations.send_invitation_email()` helper using
  `EmailMultiAlternatives`. Templates in `madga/emails/invitation.{txt,html}`.
- `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` in the
  dev `testproject` settings (and the gitignored miscoreblog).
- Integration test suite under `tests/` covering post lifecycle, page
  rendering, block registry, headless API, and invitations. 16 tests pass
  in ~2s. `pip install -e .[test]` then `pytest tests/`.
- `README.md` with install, wire-up, custom block recipes, theming.

### Changed
- `register_block_type()` now validates `key`, `label`, `template`, and
  `fields` at registration time. Loud `ValueError` instead of silent
  half-broken types in the studio. Re-registering a key logs a warning.

### Notes
- `link` is NOT an Editor.js core inline tool; previous versions' editor
  wired `'link'` in `inlineToolbar` which crashed init silently. The
  templates now use `editorjs-hyperlink@1.0.6` registered as
  `hyperlink: { class: Hyperlink }`.

## [0.1.0] — 2026-05-09

### Added — block registry & extensibility
- `madga.blocks` module: `BlockType`, `Field` hierarchy
  (`Text`, `Url`, `Int`, `Choice`, `Image`, `List`), `register_block_type`.
- `madga.templatetags.madga_blocks.render_block` dispatches a HomepageBlock
  to its registered template; `media_url` / `media_alt` filters resolve
  MediaFile UUIDs in templates.
- 6 default block types in `madga.blocks.builtin`: hero, recent_posts,
  featured_post, newsletter, text, cta — each with their public template.

### Added — Etapa 4 polish
- Pagination on the Posts list (20/page).
- Toast/snackbar global subscribed to Django messages, auto-dismiss 4s.
- `data-madga-confirm="message"` modal replacing native `confirm()`.
- Dashboard: time-aware greeting (Buenos días/tardes/noches), real
  sparklines from daily counts (last 14 days), deltas with %,
  per-post deterministic gradient thumbnails, real activity feed.
- Settings split into 4 tabs (General / Marca / SEO / Integraciones).

### Added — Etapa 3 public frontend
- `HomepageView` iterates `HomepageBlock` rows; falls back to a generic
  recent-posts list when no blocks configured.
- `RobotsTxtView`, `SitemapView`, `RssFeedView` (no third-party deps).
- Theme template chain: `madga/themes/{site.theme}/{view}.html` →
  `madga/blog/{view}.html`.
- `Site.google_analytics_id` and `Site.facebook_pixel_id` fields.
  `{% madga_tracking site %}` inclusion tag injects GA4 + Meta Pixel
  script blocks conditionally.

### Added — Etapa 2
- Homepage builder UI: per-block-type forms with curated fields. Up/down
  arrows for reordering, eye toggle for visibility, delete with confirm.

### Added — Etapa 1
- Featured image card in the editor rail (post + page editor).
- Reusable media picker modal at `/studio/media/picker/` with HTMX search
  and type filter.
- Google-style SERP preview card under SEO. Live character counters on
  Excerpt, Meta title, Meta description.
- Editor.js inline tools: explicit `inlineToolbar` array with marker,
  inline-code, underline, hyperlink registered.

### Fixed
- "Publicar" button was always saving as draft due to dual `name="status"`
  inputs colliding (rail select + action buttons).
- "Live" link from the editor 404'd on drafts; now hidden until published.
- Studio responsive: viewport meta fixed, sidebar drawer below 900px,
  editor stacks to one column, tables collapse to cards below 600px.
- Dashboard, Settings, post_edit, page_edit had several multi-line
  `{# ... #}` Django comments leaking as raw text (Django comments are
  single-line only).

### Removed
- Unused `nitro/` library deleted from the repo. madga has zero `from nitro`
  imports; if needed later it'll be a real dependency.

## [0.0.1] — 2026-05-09

Initial commit. Studio MVP, Editor.js, Django Ninja API, public blog
templates, prototype-to-Tailwind+components port.
