"""Built-in themes shipped with MADGA core."""

from django.utils.translation import gettext_lazy as _

from .registry import Theme, register_theme


@register_theme
class DefaultTheme(Theme):
    key = "default"
    label = _("Default")
    description = _("MADGA's stock theme. Tailwind-driven, generous whitespace, sans-serif throughout.")
    author = "MADGA"
    accent_color = "#6C63FF"
    heading_font = "Geist"
    body_font = "Geist"


@register_theme
class EssayTheme(Theme):
    key = "essay"
    label = _("Essay")
    description = _("Personal-blog feel. Wider type, longform-friendly. Best with detail-longform layout.")
    author = "MADGA"
    accent_color = "#1f7a4d"
    heading_font = "Source Serif 4"
    body_font = "Source Serif 4"


@register_theme
class MinimalTheme(Theme):
    key = "minimal"
    label = _("Minimal")
    description = _("Stripped-down everything. Tiny date column + post titles. Pairs with home-minimal + list-compact.")
    author = "MADGA"
    accent_color = "#000000"
    heading_font = "Geist"
    body_font = "Geist"


@register_theme
class MagazineTheme(Theme):
    key = "magazine"
    label = _("Magazine")
    description = _("Editorial home with hero post + 4-up grid. Pairs with home-editorial + list-grid.")
    author = "MADGA"
    accent_color = "#cc3333"
    heading_font = "Geist"
    body_font = "Geist"
