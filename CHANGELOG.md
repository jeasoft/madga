# CHANGELOG

All notable changes to MADGA. Format roughly follows [Keep a Changelog](https://keepachangelog.com/).

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
