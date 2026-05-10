"""Theme registry. Same shape as madga.blocks but for whole-site themes.

Sites pick a theme via Site.theme = key. Public templates resolve via
``madga/themes/<theme_key>/<view>.html`` first, falling back to the
generic ``madga/blog/<view>.html``.

Apps register themes in their AppConfig.ready(); the studio's theme
gallery (/studio/theme-gallery/) lists all registered themes with
preview cards and a one-click "Activate" action.

Usage::

    from madga.themes import Theme, register_theme

    @register_theme
    class WarmTheme(Theme):
        key = "warm"
        label = "Warm"
        description = "Cream background, generous whitespace, serif headings."
        author = "MADGA"
        accent_color = "#E67522"
        heading_font = "Source Serif 4"
        # template_dir defaults to "madga/themes/<key>/"
"""

from .registry import Theme, all_themes, get_theme, register_theme

__all__ = ["Theme", "register_theme", "get_theme", "all_themes"]
