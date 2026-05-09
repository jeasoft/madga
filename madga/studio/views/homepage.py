"""Studio homepage blocks builder (v0.2)."""

import json

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from madga.models import HomepageBlock

from ..mixins import MadgaStudioMixin


# Default config skeletons per block_type, used when a new block is created.
_DEFAULT_CONFIG = {
    HomepageBlock.BLOCK_HERO: {
        "title": "Bienvenido",
        "subtitle": "Subtítulo del hero",
        "cta_label": "Saber más",
        "cta_url": "/blog/",
    },
    HomepageBlock.BLOCK_RECENT_POSTS: {"title": "Últimas publicaciones", "count": 3},
    HomepageBlock.BLOCK_FEATURED_POST: {"slug": ""},
    HomepageBlock.BLOCK_NEWSLETTER: {
        "title": "Suscríbete",
        "subtitle": "Una vez al mes, sin spam.",
        "button_label": "Suscribirme",
    },
    HomepageBlock.BLOCK_TEXT: {"title": "", "body": ""},
    HomepageBlock.BLOCK_CTA: {
        "title": "Llamada a la acción",
        "cta_label": "Empezar",
        "cta_url": "/blog/",
    },
}


class HomepageBuilderView(MadgaStudioMixin, View):
    """Editor de bloques de la homepage.

    Acciones (POST con ``action``): ``create``, ``update``, ``delete``,
    ``toggle_visibility``. ``config`` se edita como JSON en un textarea para
    mantener el editor genérico — el mapeo a UI específica por tipo se
    consume desde el frontend público a través de la API.
    """

    template_name = "madga/studio/homepage.html"

    def _render(self, request, site):
        blocks = (
            HomepageBlock.objects.filter(site=site)
            if site
            else HomepageBlock.objects.none()
        )
        # Pre-serialize config so the textarea shows pretty JSON.
        block_rows = []
        for b in blocks:
            block_rows.append(
                {
                    "obj": b,
                    "config_json": json.dumps(b.config or {}, indent=2, ensure_ascii=False),
                }
            )
        return render(
            request,
            self.template_name,
            {
                "blocks": block_rows,
                "block_types": HomepageBlock.BLOCK_TYPE_CHOICES,
                "site": site,
                "membership": self.get_membership(),
            },
        )

    def get(self, request):
        return self._render(request, self.get_site())

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:homepage_builder")
        site = self.get_site()
        if site is None:
            messages.error(request, "No hay site activo.")
            return redirect("madga_studio:homepage_builder")

        action = request.POST.get("action") or "create"

        if action == "create":
            block_type = request.POST.get("block_type")
            valid = {k for k, _ in HomepageBlock.BLOCK_TYPE_CHOICES}
            if block_type not in valid:
                messages.error(request, "Tipo de bloque inválido.")
                return redirect("madga_studio:homepage_builder")
            next_order = (
                HomepageBlock.objects.filter(site=site).count() + 1
            )
            HomepageBlock.objects.create(
                site=site,
                block_type=block_type,
                config=_DEFAULT_CONFIG.get(block_type, {}),
                sort_order=next_order,
            )
            messages.success(request, "Bloque añadido.")

        elif action == "update":
            pk = request.POST.get("pk")
            block = get_object_or_404(
                HomepageBlock.objects.filter(site=site), pk=pk
            )
            raw_config = request.POST.get("config") or "{}"
            try:
                block.config = json.loads(raw_config)
            except json.JSONDecodeError:
                messages.error(
                    request, f"JSON inválido en el bloque #{block.pk}."
                )
                return redirect("madga_studio:homepage_builder")
            try:
                block.sort_order = int(request.POST.get("sort_order") or 0)
            except ValueError:
                pass
            block.is_visible = bool(request.POST.get("is_visible"))
            block.save()
            messages.success(request, "Bloque actualizado.")

        elif action == "delete":
            pk = request.POST.get("pk")
            HomepageBlock.objects.filter(site=site, pk=pk).delete()
            messages.success(request, "Bloque eliminado.")

        elif action == "toggle_visibility":
            pk = request.POST.get("pk")
            block = HomepageBlock.objects.filter(site=site, pk=pk).first()
            if block:
                block.is_visible = not block.is_visible
                block.save(update_fields=["is_visible", "updated_at"])

        return redirect("madga_studio:homepage_builder")
