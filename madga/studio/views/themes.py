"""Studio Theme Gallery — list + activate registered themes."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from madga.themes import all_themes, get_theme

from ..mixins import MadgaStudioMixin


class ThemeGalleryView(MadgaStudioMixin, View):
    template_name = "madga/studio/theme_gallery.html"

    def get(self, request):
        site = self.get_site()
        return render(request, self.template_name, {
            "themes": all_themes(),
            "site": site,
            "membership": self.get_membership(),
        })

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:theme_gallery")
        site = self.get_site()
        if site is None:
            messages.error(request, "No hay site activo.")
            return redirect("madga_studio:theme_gallery")

        action = request.POST.get("action")
        key = request.POST.get("theme")
        theme = get_theme(key) if key else None
        if theme is None:
            messages.error(request, "Theme no encontrado.")
            return redirect("madga_studio:theme_gallery")

        if action == "activate":
            site.theme = theme.key
            site.save(update_fields=["theme"])
            messages.success(request, f"Theme '{theme.label}' activado.")
        elif action == "activate_with_palette":
            theme.apply_palette(site)
            messages.success(
                request,
                f"Theme '{theme.label}' activado con su paleta (colores + fuentes).",
            )

        return redirect("madga_studio:theme_gallery")
