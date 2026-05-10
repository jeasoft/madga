"""Theme registry."""

from __future__ import annotations

import logging
from typing import Optional


_REGISTRY: dict[str, "Theme"] = {}
log = logging.getLogger("madga.themes")


class Theme:
    """A site-wide theme. Subclass + decorate with @register_theme.

    Attributes:
      key:           short stable identifier (e.g. "default", "warm").
      label:         display name in the gallery.
      description:   one-line subtitle.
      author:        attribution shown in the card.
      preview_image: path under STATIC for a screenshot (optional).
      accent_color:  default accent suggested when the theme is activated
                     (the user's existing Site.accent_color is preserved
                     unless ``apply_palette()`` is called).
      heading_font / body_font: same idea — defaults the theme suggests.
    """

    key: str = ""
    label: str = ""
    description: str = ""
    author: str = ""
    preview_image: str = ""
    accent_color: str = ""
    heading_font: str = ""
    body_font: str = ""

    @property
    def template_dir(self) -> str:
        return f"madga/themes/{self.key}/"

    def apply_palette(self, site):
        """Optionally call from the studio when activating this theme.
        Sets accent + fonts on the Site if the theme declares them."""
        update_fields = ["theme"]
        site.theme = self.key
        if self.accent_color:
            site.accent_color = self.accent_color
            update_fields.append("accent_color")
        if self.heading_font:
            site.heading_font = self.heading_font
            update_fields.append("heading_font")
        if self.body_font:
            site.body_font = self.body_font
            update_fields.append("body_font")
        site.save(update_fields=update_fields)


def register_theme(cls):
    """Class decorator. Validates required attrs at registration time."""
    name = cls.__name__
    if not getattr(cls, "key", ""):
        raise ValueError(f"{name} must define a non-empty `key`.")
    if not getattr(cls, "label", ""):
        raise ValueError(f"{name} (key={cls.key!r}) must define `label`.")
    if cls.key in _REGISTRY:
        log.warning(
            "Theme %r is being re-registered: %s overrides %s",
            cls.key, name, type(_REGISTRY[cls.key]).__name__,
        )
    _REGISTRY[cls.key] = cls()
    return cls


def get_theme(key: str) -> Optional[Theme]:
    return _REGISTRY.get(key)


def all_themes() -> list[Theme]:
    return list(_REGISTRY.values())
