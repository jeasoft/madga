"""Studio Settings + theme/layouts (v0.2)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from ..forms import SiteSettingsForm
from ..mixins import MadgaStudioMixin


# Tabs for the Settings page. Each tab declares which form fields it owns;
# the rendering loops over field names so order is template-controlled.
SETTINGS_TABS = [
    {
        "key": "general",
        "label": _("General"),
        "fields": ["name", "domain", "description", "logo", "favicon", "timezone"],
    },
    {
        "key": "branding",
        "label": _("Branding"),
        "fields": [
            "accent_color", "heading_font", "body_font",
            "border_radius", "content_density", "color_scheme", "theme",
        ],
    },
    {
        "key": "seo",
        "label": _("SEO"),
        "fields": ["meta_title", "meta_description"],
    },
    {
        "key": "integrations",
        "label": _("Integrations"),
        "fields": ["google_analytics_id", "facebook_pixel_id"],
    },
]


class SettingsView(MadgaStudioMixin, View):
    template_name = "madga/studio/settings.html"

    def _resolve_tab(self, request) -> str:
        wanted = request.GET.get("tab") or "general"
        for t in SETTINGS_TABS:
            if t["key"] == wanted:
                return wanted
        return "general"

    def _ctx(self, form, site, current_tab):
        # Build a dict of {field_name: BoundField} so the template can render
        # each tab's fields in the curated order without a {% if name == … %}
        # cascade.
        bound = {f.name: f for f in form}
        return {
            "form": form,
            "site": site,
            "membership": self.get_membership(),
            "tabs": SETTINGS_TABS,
            "current_tab": current_tab,
            "bound": bound,
        }

    def get(self, request):
        site = self.get_site()
        tab = self._resolve_tab(request)
        return render(request, self.template_name, self._ctx(SiteSettingsForm(instance=site), site, tab))

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, _("Permiso denegado."))
            return redirect("madga_studio:settings")
        site = self.get_site()
        tab = request.POST.get("active_tab") or self._resolve_tab(request)
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, _("Settings actualizados."))
            url = "/studio/settings/"
            if tab and tab != "general":
                url += f"?tab={tab}"
            return redirect(url)
        return render(request, self.template_name, self._ctx(form, site, tab))


class ThemeView(MadgaStudioMixin, View):
    """v0.2: editor de tokens visuales del site con preview en vivo.

    Reuses ``SiteSettingsForm`` so the persistence layer matches Settings.
    """

    template_name = "madga/studio/theme.html"

    FONT_CHOICES = [
        "Geist", "Inter", "Roboto", "Source Sans Pro", "Open Sans",
        "Lora", "Merriweather", "Playfair Display", "Geist Mono", "JetBrains Mono",
    ]
    THEME_OPTIONS = ["essay", "magazine", "docs", "minimal"]

    def _render(self, request, form, site):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "site": site,
                "membership": self.get_membership(),
                "font_choices": self.FONT_CHOICES,
                "theme_options": self.THEME_OPTIONS,
            },
        )

    def get(self, request):
        site = self.get_site()
        return self._render(request, SiteSettingsForm(instance=site), site)

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, _("Permiso denegado."))
            return redirect("madga_studio:theme")
        site = self.get_site()
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, _("Theme actualizado."))
            return redirect("madga_studio:theme")
        return self._render(request, form, site)


LAYOUT_CHOICES = {
    "home": [
        ("default", _("Default"), _("HomepageBlocks-driven home (recommended).")),
        ("editorial", _("Editorial"), _("Hero + curated articles in a magazine grid.")),
        ("minimal", _("Minimal"), _("Just the most-recent posts in a clean list.")),
    ],
    "list": [
        ("default", _("Default"), _("Chronological list with category filters.")),
        ("grid", _("Grid"), _("Cards with thumbnails, 2 columns.")),
        ("compact", _("Compact"), _("Title + date, no excerpt, dense.")),
    ],
    "detail": [
        ("default", _("Default"), _("Centered article column with featured image hero.")),
        ("longform", _("Longform"), _("Wider column, drop caps, larger type.")),
        ("docs", _("Docs"), _("Sidebar TOC + content.")),
    ],
    "page": [
        ("simple", _("Simple"), _("Centered prose. Good for legal pages.")),
        ("sidebar", _("Sidebar"), _("Right sidebar with table of contents.")),
        ("docs", _("Docs"), _("Left sidebar with sibling pages.")),
    ],
}


class LayoutsView(MadgaStudioMixin, View):
    """Layout selector per content-type. Selections persist on Site.settings."""

    template_name = "madga/studio/layouts.html"

    def _current_selection(self, site) -> dict:
        s = (site.settings if site else {}) or {}
        return {
            "home":   s.get("layout_home", "default"),
            "list":   s.get("layout_list", "default"),
            "detail": s.get("layout_detail", "default"),
            "page":   s.get("layout_page", "simple"),
        }

    def get(self, request):
        site = self.get_site()
        return render(request, self.template_name, {
            "site": site,
            "membership": self.get_membership(),
            "groups": LAYOUT_CHOICES,
            "selection": self._current_selection(site),
        })

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, _("Permiso denegado."))
            return redirect("madga_studio:layouts")
        site = self.get_site()
        if site is None:
            messages.error(request, _("No hay site activo."))
            return redirect("madga_studio:layouts")

        new_settings = dict(site.settings or {})
        for kind, options in LAYOUT_CHOICES.items():
            valid = {key for key, _, _ in options}
            chosen = request.POST.get(f"layout_{kind}")
            if chosen in valid:
                new_settings[f"layout_{kind}"] = chosen
        site.settings = new_settings
        site.save(update_fields=["settings"])
        messages.success(request, _("Layouts actualizados."))
        return redirect("madga_studio:layouts")
