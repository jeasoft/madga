"""Render Editor.js JSON to HTML for the public blog and API."""

import html as html_lib

SUPPORTED_BLOCKS = {
    "paragraph",
    "header",
    "list",
    "quote",
    "code",
    "delimiter",
    "image",
    "embed",
}


def _esc(value: str) -> str:
    return html_lib.escape(value or "", quote=True)


def render_blocks(data: dict | None) -> str:
    """Convert Editor.js JSON to HTML."""
    if not data:
        return ""
    blocks = data.get("blocks") or []
    parts: list[str] = []

    for block in blocks:
        t = block.get("type")
        d = block.get("data") or {}

        if t == "paragraph":
            text = d.get("text", "")
            parts.append(f"<p>{text}</p>")

        elif t == "header":
            level = int(d.get("level", 2))
            level = max(1, min(6, level))
            parts.append(f"<h{level}>{d.get('text', '')}</h{level}>")

        elif t == "list":
            tag = "ol" if d.get("style") == "ordered" else "ul"
            items_html = "".join(
                f"<li>{item}</li>" for item in (d.get("items") or [])
            )
            parts.append(f"<{tag}>{items_html}</{tag}>")

        elif t == "quote":
            caption = d.get("caption")
            cite = f"<cite>{caption}</cite>" if caption else ""
            parts.append(
                f"<blockquote><p>{d.get('text', '')}</p>{cite}</blockquote>"
            )

        elif t == "code":
            code = _esc(d.get("code", ""))
            parts.append(f"<pre><code>{code}</code></pre>")

        elif t == "delimiter":
            parts.append("<hr>")

        elif t == "image":
            file = d.get("file") or {}
            url = _esc(file.get("url", ""))
            caption = d.get("caption", "")
            alt = _esc(caption)
            cap_html = f"<figcaption>{caption}</figcaption>" if caption else ""
            stretched = " class=\"stretched\"" if d.get("stretched") else ""
            parts.append(
                f'<figure{stretched}><img src="{url}" alt="{alt}" loading="lazy">'
                f"{cap_html}</figure>"
            )

        elif t == "embed":
            src = _esc(d.get("embed", ""))
            caption = d.get("caption", "")
            cap_html = f"<figcaption>{caption}</figcaption>" if caption else ""
            parts.append(
                f'<figure class="embed-container">'
                f'<iframe src="{src}" frameborder="0" allowfullscreen '
                f'loading="lazy"></iframe>{cap_html}</figure>'
            )

    return "\n".join(parts)
