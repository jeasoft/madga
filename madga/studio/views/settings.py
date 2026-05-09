"""Studio Settings + theme/layouts (v0.2)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from ..forms import SiteSettingsForm
from ..mixins import MadgaStudioMixin


class SettingsView(MadgaStudioMixin, View):
    template_name = "madga/studio/settings.html"

    def get(self, request):
        site = self.get_site()
        return render(
            request,
            self.template_name,
            {
                "form": SiteSettingsForm(instance=site),
                "site": site,
                "membership": self.get_membership(),
            },
        )

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:settings")
        site = self.get_site()
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings actualizados.")
            return redirect("madga_studio:settings")
        return render(
            request,
            self.template_name,
            {"form": form, "site": site, "membership": self.get_membership()},
        )


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
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:theme")
        site = self.get_site()
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Theme actualizado.")
            return redirect("madga_studio:theme")
        return self._render(request, form, site)


class LayoutsView(MadgaStudioMixin, TemplateView):
    """v0.2: layout selector por tipo de página."""
    template_name = "madga/studio/layouts.html"
