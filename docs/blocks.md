# Custom block types

MADGA's homepage builder reads from a block registry. Built-in types
include Hero, Recent posts, Featured post, Newsletter, Text, CTA,
Contact form. Host projects add their own with a decorator + a
template — no migrations, no studio code changes.

```python
# myapp/blocks.py
from madga.blocks import (
    BlockType, register_block_type,
    TextField, UrlField, ImageField, ListField,
)

@register_block_type
class TestimonialGridBlock(BlockType):
    key = "myapp_testimonials"
    label = "Testimonials grid"
    description = "Cards with quote + photo + role."
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

```python
# myapp/apps.py
class MyAppConfig(AppConfig):
    name = "myapp"
    def ready(self):
        from . import blocks  # noqa: F401  registers via decorator
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

## Field types

| Field | Stored as | Studio widget |
|---|---|---|
| `TextField` | str | `<input>` or `<textarea>` (`multiline=True`) |
| `UrlField` | str | `<input type=url>` (accepts local paths too) |
| `IntField` | int | `<input type=number>` |
| `ChoiceField` | str | `<select>` |
| `ImageField` | MediaFile UUID (str) | Featured-image picker (modal) |
| `ListField` | list[dict] | Repeatable sub-form with add/remove |

## Template filters

`{% load madga_blocks %}` exposes:

- `{{ uuid_string|media_url }}` → `MediaFile.file.url`
- `{{ uuid_string|media_alt }}` → `MediaFile.alt_text` or filename
- `{% render_block block %}` — render a single block via its registered template
