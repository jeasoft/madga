"""Reusable template tags for the MADGA Studio (Nitro-style).

All tags render small, focused components. Keep markup in templates under
``madga/templates/madga/studio/components/`` and use these tags as the
ergonomic entry point.
"""

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


# ---------------------------------------------------------------------------
# SVG icons — single source of truth, used by every component.
# Stroke-based heroicons-style icons (currentColor, stroke-width 1.8 default).
# ---------------------------------------------------------------------------
ICON_PATHS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
    "post": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>',
    "page": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    "media": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
    "tag": '<path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    "broadcast": '<path d="M4 11a8 8 0 0 1 8-8"/><path d="M4 16a13 13 0 0 1 13-13"/><circle cx="5" cy="19" r="2"/>',
    "theme": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 0 20"/><path d="M12 2a15.3 15.3 0 0 0 0 20"/>',
    "layouts": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "navigation": '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "homepage": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "minus": '<line x1="5" y1="12" x2="19" y2="12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
    "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "sort": '<path d="M3 6h18M6 12h12M10 18h4"/>',
    "external": '<path d="M7 17L17 7"/><path d="M9 7h8v8"/>',
    "more-h": '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    "more-v": '<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>',
    "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
    "chevron-up": '<polyline points="18 15 12 9 6 15"/>',
    "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
    "chevron-left": '<polyline points="15 18 9 12 15 6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a13.5 13.5 0 0 1 0 18"/><path d="M12 3a13.5 13.5 0 0 0 0 18"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "menu": '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "mail": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    "refresh-cw": '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
}


@register.simple_tag
def studio_icon(name: str, size: int = 16, stroke: float = 1.8, css_class: str = ""):
    """Render a stroke-based SVG icon. Falls back silently if name unknown."""
    body = ICON_PATHS.get(name)
    if not body:
        return ""
    cls = f' class="{css_class}"' if css_class else ""
    return mark_safe(
        f'<svg{cls} width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


@register.inclusion_tag("madga/studio/components/badge.html")
def studio_badge(status: str, label: str = ""):
    """Status badge. status ∈ {published, draft, scheduled, archived}."""
    return {"status": status, "label": label or status.title()}


@register.simple_tag
def studio_btn(label: str, href: str = "", variant: str = "default",
               size: str = "", icon: str = "", type: str = "button",
               css_class: str = "", target: str = "", disabled: bool = False,
               **attrs):
    """Button or link styled as one. Variants: default, primary, ghost, danger.
    Sizes: '' (default), sm.
    """
    classes = ["madga-btn"]
    if variant != "default":
        classes.append(f"madga-btn--{variant}")
    if size:
        classes.append(f"madga-btn--{size}")
    if css_class:
        classes.append(css_class)

    icon_html = ""
    if icon:
        icon_html = studio_icon(icon, 14 if size == "sm" else 14)

    attr_str = ""
    if target:
        attr_str += f' target="{target}"'
    for k, v in attrs.items():
        attr_str += f' {k.replace("_", "-")}="{v}"'

    cls = " ".join(classes)
    aria_disabled = ' aria-disabled="true"' if disabled else ""
    if href:
        return mark_safe(
            f'<a class="{cls}" href="{href}"{attr_str}{aria_disabled}>'
            f'{icon_html}{label}</a>'
        )
    disabled_attr = " disabled" if disabled else ""
    return mark_safe(
        f'<button class="{cls}" type="{type}"{attr_str}{disabled_attr}>'
        f"{icon_html}{label}</button>"
    )


@register.inclusion_tag("madga/studio/components/page_header.html", takes_context=True)
def studio_page_header(context, title: str, subtitle: str = ""):
    """Page header (title + subtitle) — slot in the calling template's actions block."""
    return {"title": title, "subtitle": subtitle, "request": context.get("request")}


@register.inclusion_tag("madga/studio/components/stat_card.html")
def studio_stat_card(label: str, value, icon: str = "", meta: str = "",
                     delta: str = "", delta_dir: str = ""):
    """Stat card. delta_dir ∈ {up, down, ''}."""
    return {
        "label": label, "value": value, "icon": icon,
        "meta": meta, "delta": delta, "delta_dir": delta_dir,
    }


@register.inclusion_tag("madga/studio/components/empty_state.html")
def studio_empty(title: str, message: str = "", action_label: str = "",
                 action_href: str = ""):
    return {
        "title": title, "message": message,
        "action_label": action_label, "action_href": action_href,
    }


@register.filter
def get_item(d, key):
    """Dict lookup from templates: {{ mydict|get_item:keyvar }}."""
    if not isinstance(d, dict):
        return ""
    return d.get(key, "")


# 9 hand-tuned gradient stops, deterministic per object so a Post always
# renders with the same thumb until its id/slug changes.
_THUMB_GRADIENTS = [
    "linear-gradient(135deg, #7C5CFF, #FF7A59)",
    "linear-gradient(135deg, #06B6D4, #6366F1)",
    "linear-gradient(135deg, #F59E0B, #EF4444)",
    "linear-gradient(135deg, #10B981, #06B6D4)",
    "linear-gradient(135deg, #EC4899, #8B5CF6)",
    "linear-gradient(135deg, #6366F1, #06B6D4)",
    "linear-gradient(135deg, #F472B6, #FB923C)",
    "linear-gradient(135deg, #2DD4BF, #6366F1)",
    "linear-gradient(135deg, #A855F7, #EC4899)",
]


@register.filter
def thumb_gradient(seed) -> str:
    """Return a CSS background gradient deterministic from any value."""
    s = str(seed or "")
    if not s:
        return _THUMB_GRADIENTS[0]
    h = sum(ord(c) for c in s)
    return _THUMB_GRADIENTS[h % len(_THUMB_GRADIENTS)]


@register.simple_tag
def madga_setup_body(body: str):
    """Render an OAuth setup step body with ``<copy>...</copy>`` chunks
    promoted to a copy-paste-friendly ``<pre>`` block. Plain text
    outside the markers stays as a paragraph.

    The body string can contain newlines and the marker can wrap
    multi-line code (settings.py snippets, URLs, etc.). Output is
    safe HTML (escaped before mark_safe).
    """
    from django.utils.html import escape
    import re

    pattern = re.compile(r"<copy>(.*?)</copy>", re.DOTALL)
    out: list[str] = []
    pos = 0
    for m in pattern.finditer(body or ""):
        before = (body or "")[pos:m.start()]
        if before.strip():
            out.append(f"<p>{escape(before).replace(chr(10), '<br>')}</p>")
        code = escape(m.group(1).strip())
        out.append(
            f'<pre class="madga-setup-copy" data-copy>{code}'
            f'<button type="button" class="madga-setup-copy-btn" '
            f'onclick="navigator.clipboard.writeText(this.previousSibling.nodeValue || '
            f"this.parentNode.firstChild.textContent); this.textContent='Copied'\">Copy</button>"
            f"</pre>"
        )
        pos = m.end()
    tail = (body or "")[pos:]
    if tail.strip():
        out.append(f"<p>{escape(tail).replace(chr(10), '<br>')}</p>")
    return mark_safe("".join(out))


@register.simple_tag
def studio_active(request, *url_names) -> str:
    """Return ``is-active`` if the current resolved url_name matches any given."""
    if not request:
        return ""
    name = getattr(getattr(request, "resolver_match", None), "url_name", None)
    if name and name in url_names:
        return "is-active"
    # Match by prefix (e.g. all post_* views)
    if name:
        for prefix in url_names:
            if prefix.endswith("*") and name.startswith(prefix[:-1]):
                return "is-active"
    return ""
