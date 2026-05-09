"""Field types for declarative block-type schemas.

Each Field knows three things:

- how to coerce a value out of a Django POST QueryDict (``coerce_from_post``)
- how to render an input element for the studio form (``render_input``)
- a default value used when a new block is created (``default_value``)

The ListField is special: it carries a list of ``item_fields`` and serializes
to a JSON list of dicts. Inputs are named ``<list>__<idx>__<sub>`` so they
group cleanly when posted back.
"""

from __future__ import annotations

from html import escape
from typing import Any

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class Field:
    """Base class. Subclasses customise render_input + coerce_from_post."""

    kind: str = "text"

    def __init__(
        self,
        name: str,
        label: str,
        *,
        help_text: str = "",
        default: Any = "",
        placeholder: str = "",
    ):
        self.name = name
        self.label = label
        self.help_text = help_text
        self.default = default
        self.placeholder = placeholder

    # Subclasses override:
    def coerce_from_post(self, post, prefix: str = ""):
        return post.get(prefix + self.name, self.default)

    def render_input(self, value, prefix: str = "") -> str:
        v = "" if value is None else escape(str(value))
        return mark_safe(
            f'<input class="madga-input" type="text" name="{prefix}{self.name}" '
            f'value="{v}" placeholder="{escape(self.placeholder)}">'
        )

    def default_value(self):
        return self.default


class TextField(Field):
    """Plain single-line text. Pass multiline=True to get a textarea."""

    def __init__(self, name, label, *, multiline: bool = False, rows: int = 3, **kw):
        self.multiline = multiline
        self.rows = rows
        super().__init__(name, label, **kw)

    def render_input(self, value, prefix=""):
        v = "" if value is None else escape(str(value))
        ph = escape(self.placeholder)
        if self.multiline:
            return mark_safe(
                f'<textarea class="madga-textarea" name="{prefix}{self.name}" '
                f'rows="{self.rows}" placeholder="{ph}">{v}</textarea>'
            )
        return mark_safe(
            f'<input class="madga-input" type="text" name="{prefix}{self.name}" '
            f'value="{v}" placeholder="{ph}">'
        )


class UrlField(Field):
    kind = "url"

    def render_input(self, value, prefix=""):
        v = "" if value is None else escape(str(value))
        return mark_safe(
            f'<input class="madga-input" type="url" name="{prefix}{self.name}" '
            f'value="{v}" placeholder="https://… o /ruta">'
        )


class IntField(Field):
    kind = "int"

    def __init__(self, name, label, *, min: int = 0, max: int = 100, **kw):
        kw.setdefault("default", 0)
        super().__init__(name, label, **kw)
        self.min, self.max = min, max

    def coerce_from_post(self, post, prefix=""):
        try:
            return int(post.get(prefix + self.name, self.default) or 0)
        except (ValueError, TypeError):
            return 0

    def render_input(self, value, prefix=""):
        v = 0 if value is None else int(value or 0)
        return mark_safe(
            f'<input class="madga-input" type="number" name="{prefix}{self.name}" '
            f'value="{v}" min="{self.min}" max="{self.max}" style="width:120px;">'
        )


class ChoiceField(Field):
    kind = "choice"

    def __init__(self, name, label, *, choices: list[tuple[str, str]], **kw):
        self.choices = choices
        super().__init__(name, label, **kw)

    def render_input(self, value, prefix=""):
        opts = []
        for k, l in self.choices:
            sel = " selected" if str(value) == str(k) else ""
            opts.append(f'<option value="{escape(k)}"{sel}>{escape(l)}</option>')
        return mark_safe(
            f'<select class="madga-select" name="{prefix}{self.name}">'
            + "".join(opts) + "</select>"
        )


class ImageField(Field):
    """Stores a MediaFile id (UUID string). Renders as the existing
    featured-image picker so it integrates with the media-library modal."""

    kind = "image"

    def coerce_from_post(self, post, prefix=""):
        # Empty string means "cleared".
        return post.get(prefix + self.name, "") or ""

    def render_input(self, value, prefix=""):
        from madga.models import MediaFile

        media = None
        if value:
            try:
                media = MediaFile.objects.filter(pk=value).first()
            except Exception:
                media = None
        return render_to_string(
            "madga/studio/components/featured_image_field.html",
            {"name": prefix + self.name, "media": media},
        )


class ListField(Field):
    """A list of records, each with ``item_fields`` sub-fields.

    POST inputs use the convention ``<list>__<idx>__<sub>``. We collect them
    grouped by idx, run each sub-field's coerce, and return a list ordered by
    the indices that appeared. Items where ALL sub-values are empty are
    dropped (safety net for a half-typed new row).
    """

    kind = "list"

    def __init__(
        self,
        name,
        label,
        *,
        item_fields: list[Field],
        item_label: str = "Item",
        max_items: int = 20,
        **kw,
    ):
        self.item_fields = item_fields
        self.item_label = item_label
        self.max_items = max_items
        kw.setdefault("default", [])
        super().__init__(name, label, **kw)

    def default_value(self):
        return []

    def coerce_from_post(self, post, prefix=""):
        full_prefix = prefix + self.name + "__"
        # Map idx → {sub_name: raw_value}
        raw_by_idx: dict[int, dict] = {}
        for key in post.keys():
            if not key.startswith(full_prefix):
                continue
            tail = key[len(full_prefix):]
            try:
                idx_str, sub = tail.split("__", 1)
                idx = int(idx_str)
            except (ValueError, IndexError):
                continue
            raw_by_idx.setdefault(idx, {})
            for sf in self.item_fields:
                if sf.name == sub:
                    raw_by_idx[idx][sf.name] = sf.coerce_from_post(
                        post, prefix=f"{full_prefix}{idx}__"
                    )
                    break

        # Sort by idx, drop empty rows.
        items: list[dict] = []
        for idx in sorted(raw_by_idx.keys()):
            row = raw_by_idx[idx]
            if any(v for v in row.values()):
                # Make sure every sub-field is present (with default if missing).
                full_row = {sf.name: row.get(sf.name, sf.default_value()) for sf in self.item_fields}
                items.append(full_row)
        return items

    def render_input(self, value, prefix=""):
        from django.template.loader import render_to_string as rts

        items = value or []
        list_prefix = prefix + self.name + "__"

        def _row(idx, data):
            sub_prefix = f"{list_prefix}{idx}__"
            return {
                "idx": idx,
                "human_idx": idx + 1,
                "fields": [
                    {
                        "label": sf.label,
                        "name": sf.name,
                        "html": sf.render_input(data.get(sf.name, sf.default_value()), prefix=sub_prefix),
                    }
                    for sf in self.item_fields
                ],
            }

        items_render = [_row(i, item) for i, item in enumerate(items)]
        # The template (hidden, cloned by JS for new items) uses __INDEX__ as placeholder.
        template_render = {
            "fields": [
                {
                    "label": sf.label,
                    "name": sf.name,
                    "html": sf.render_input(sf.default_value(), prefix=f"{list_prefix}__INDEX____"),
                }
                for sf in self.item_fields
            ],
        }

        return rts(
            "madga/studio/blocks/_list_field.html",
            {
                "list_field": self,
                "list_data_attr": prefix + self.name,
                "items": items_render,
                "tpl": template_render,
                "next_idx": len(items_render),
            },
        )
