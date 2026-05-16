# MADGA — Make Django Great Again

A headless-ready CMS as a Django app. Drop it into any Django project to get
a Studio backoffice, a Ninja-powered headless API, and an opinionated public
blog/page renderer — without giving up your Django stack.

```
┌──────────────────────────────────────────────────────┐
│  Studio  /studio/         Ninja API  /api/madga/v1/  │
│  (auth, posts, pages,     (public + api-key auth)    │
│  media, homepage          ─────────────────────────  │
│  builder, settings,       Public Site                │
│  themes, users)           /, /blog/, /p/<slug>/      │
└──────────────────────────────────────────────────────┘
                       madga (Django app)
```

## What's in the box

- **Models**: Site, Post, Page, Category, Tag, MediaFile, SiteUser,
  UserInvitation, HomepageBlock, NavItem.
- **Studio**: dashboard with sparklines + activity feed; Posts CRUD with
  Editor.js, featured image picker, SERP preview, char counters; Pages
  with the same surfaces; Media library with HTMX modal picker; Categories
  & tags; Users with invite-by-email flow; Settings split in 4 tabs;
  Homepage builder driven by a pluggable block registry.
- **Headless API** (Django Ninja): `/posts/`, `/posts/<slug>/`,
  `/pages/<slug>/`, `/categories/`, `/tags/`, `/navigation/`, `/homepage/`.
  Auth via per-Site API key.
- **Public site**: HomepageBlocks-driven home, blog list/detail with cached
  body_html, Page rendering with layout chain, robots.txt + sitemap.xml +
  RSS, GA4 + Meta Pixel injection.
- **Block registry**: declarative `BlockType` classes with typed Fields
  (Text, Url, Int, Choice, Image, List). Apps register their own types in
  `apps.ready()` and they appear in the homepage builder automatically.

## Install

```bash
# while it's still local-only:
uv add /path/to/madga
# or pip install -e /path/to/madga
```

`pyproject.toml` declares: Django 5.x, django-allauth[headless], django-ninja,
Pillow, python-slugify.

### Wire it into your project

```python
# settings.py
INSTALLED_APPS = [
    # ... django.contrib.* ...
    'allauth', 'allauth.account', 'allauth.headless',
    'madga',
    # your project apps
]

MIDDLEWARE = [
    # ... standard ...
    'allauth.account.middleware.AccountMiddleware',
    'madga.studio.middleware.MadgaStudioMiddleware',
]

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'madga.context_processors.current_site',
            'madga.context_processors.studio_topbar',
        ],
    },
}]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # dev
DEFAULT_FROM_EMAIL = 'noreply@yoursite.com'
```

```python
# urls.py
from django.urls import path, include
from madga.api.router import api as madga_api
from madga.urls import madga_public_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('studio/', include('madga.studio.urls')),
    path('api/madga/v1/', madga_api.urls),
    path('_allauth/', include('allauth.headless.urls')),
    path('accounts/', include('allauth.urls')),
    *madga_public_urls(),  # /, /blog/, /p/<slug>/, /robots.txt, /sitemap.xml, /rss.xml
]
```

If your project owns `/` (e.g. a custom landing view), pass
`madga_public_urls(include_homepage=False)` and route `/` yourself.

### First-run

```bash
python manage.py migrate
python manage.py createsuperuser
# Create a Site row (admin or shell):
python manage.py shell -c "
from madga.models import Site, SiteUser
from django.contrib.auth import get_user_model
s = Site.objects.create(name='My Site', domain='mysite.com')
u = get_user_model().objects.first()
SiteUser.objects.create(site=s, user=u, role='owner')
"
python manage.py runserver
# Visit /studio/
```

## Custom block types (the headline feature)

```python
# myapp/apps.py
class MyAppConfig(AppConfig):
    name = "myapp"
    def ready(self):
        from . import blocks  # noqa: F401  registers via decorators

# myapp/blocks.py
from madga.blocks import (
    BlockType, register_block_type,
    TextField, UrlField, ImageField, ListField,
)

@register_block_type
class TestimonialGridBlock(BlockType):
    key = "myapp_testimonials"
    label = "Testimonials grid"
    description = "A grid of testimonial cards."
    template = "blocks/myapp_testimonials.html"
    fields = [
        TextField("title", "Section title", default="What customers say"),
        ListField(
            "items", "Testimonials",
            item_label="Testimonial",
            item_fields=[
                ImageField("avatar", "Photo"),
                TextField("name", "Name"),
                TextField("role", "Role"),
                TextField("quote", "Quote", multiline=True),
            ],
        ),
    ]
```

```html
<!-- myapp/templates/blocks/myapp_testimonials.html -->
{% load madga_blocks %}
<section>
  <h2>{{ config.title }}</h2>
  {% for item in config.items %}
    <article>
      {% if item.avatar %}<img src="{{ item.avatar|media_url }}" alt="">{% endif %}
      <p>{{ item.quote }}</p>
      <cite>— {{ item.name }}, {{ item.role }}</cite>
    </article>
  {% endfor %}
</section>
```

That's it. The tile shows up in `/studio/homepage/` "Add a block" tray;
items can be added/removed/reordered in the form; the public homepage
renders via `{% render_block block %}`.

## Available field types

| Field | Stored as | Studio widget |
|-------|-----------|---------------|
| `TextField` | str | `<input>` or `<textarea>` (with `multiline=True`) |
| `UrlField` | str | `<input type=url>` |
| `IntField` | int | `<input type=number>` |
| `ChoiceField` | str | `<select>` |
| `ImageField` | MediaFile UUID (str) | Featured-image picker (modal) |
| `ListField` | list[dict] | Repeatable sub-form with add/remove |

Filters available in templates (load `{% load madga_blocks %}`):
- `{{ uuid_string|media_url }}` → MediaFile.file.url
- `{{ uuid_string|media_alt }}` → MediaFile.alt_text or filename

## Configuration

`madga.conf.settings` reads from a project-level `MADGA = {...}` dict:

```python
MADGA = {
    "SITE_DOMAIN": "yoursite.com",
    "DEFAULT_THEME": "default",
    "STUDIO_URL_PREFIX": "studio",
    "API_URL_PREFIX": "api/madga/v1",
    "DEFAULT_PAGINATION": 20,
    "AUTOSAVE_INTERVAL_SECONDS": 30,
}
```

## Theming

Public templates resolve via the chain
`madga/themes/{site.theme}/{home|detail|list|page}.html`
falling back to `madga/blog/...`. To create a theme, drop templates under
`yourapp/templates/madga/themes/<theme_name>/` and set
`Site.theme = "<theme_name>"`.

## Tests

```bash
pip install -e .[test]
pytest tests/
```

Integration suite covers post lifecycle, page rendering, block registry,
headless API, invitations, public signup signal, and i18n. The suite runs
against sqlite by default; CI also runs it against Postgres 16.

### Verify on Postgres locally

```bash
docker run -d --rm --name madga-pg-test \
    -e POSTGRES_PASSWORD=madga -e POSTGRES_USER=madga \
    -e POSTGRES_DB=madga_test -p 55432:5432 postgres:16-alpine

DJANGO_SETTINGS_MODULE=testproject.settings_pg pytest tests/
docker stop madga-pg-test
```

Both sqlite and Postgres are first-class targets — MADGA uses only portable
ORM primitives (`JSONField`, `TextField`, `__icontains`) and ships no raw SQL.

## Versioning

- **0.1.1** — Page featured/og image fields, public URL helper, registry
  guards, real invite emails, accept flow, integration tests, this README.
- **0.1.0** — Block registry, dashboard polish, settings tabs, toast,
  pagination, RSS/sitemap, theme system, GA4 + FB Pixel.
- **0.0.1** — Studio MVP, Editor.js, Ninja API, baseline.

See `CHANGELOG.md` for the full list.

## License

Apache 2.0 — see `LICENSE`.
