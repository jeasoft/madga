# CHANGELOG

All notable changes to MADGA. Format roughly follows [Keep a Changelog](https://keepachangelog.com/).

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
