"""Studio homepage blocks builder.

Each HomepageBlock has a free-form ``config`` JSONField, but the editor
maps known block_types to typed forms so non-technical users never see
raw JSON. Unknown keys are preserved if the model already had them.
"""

from django.contrib import messages
from django.db import transaction
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


# Fields exposed per block type. Maps form field name → (label, kind).
# kind ∈ {text, textarea, url, int}
BLOCK_FIELDS = {
    HomepageBlock.BLOCK_HERO: [
        ("title", "Título", "text"),
        ("subtitle", "Subtítulo", "textarea"),
        ("cta_label", "Texto del botón", "text"),
        ("cta_url", "Destino del botón", "url"),
    ],
    HomepageBlock.BLOCK_RECENT_POSTS: [
        ("title", "Título de la sección", "text"),
        ("count", "Cuántos posts mostrar", "int"),
    ],
    HomepageBlock.BLOCK_FEATURED_POST: [
        ("slug", "Slug del post a destacar", "text"),
    ],
    HomepageBlock.BLOCK_NEWSLETTER: [
        ("title", "Título", "text"),
        ("subtitle", "Subtítulo", "textarea"),
        ("button_label", "Texto del botón", "text"),
    ],
    HomepageBlock.BLOCK_TEXT: [
        ("title", "Título (opcional)", "text"),
        ("body", "Texto", "textarea"),
    ],
    HomepageBlock.BLOCK_CTA: [
        ("title", "Título", "text"),
        ("cta_label", "Texto del botón", "text"),
        ("cta_url", "Destino del botón", "url"),
    ],
}

BLOCK_DESCRIPTIONS = {
    HomepageBlock.BLOCK_HERO: "Bloque grande de bienvenida con título, subtítulo y un CTA.",
    HomepageBlock.BLOCK_RECENT_POSTS: "Lista de los últimos N posts publicados.",
    HomepageBlock.BLOCK_FEATURED_POST: "Un post destacado mostrado a tamaño completo.",
    HomepageBlock.BLOCK_NEWSLETTER: "Banda de suscripción al newsletter.",
    HomepageBlock.BLOCK_TEXT: "Bloque de texto libre con título opcional.",
    HomepageBlock.BLOCK_CTA: "Llamada a la acción simple con un botón.",
}


def _coerce(kind: str, raw: str):
    """Convert a POST string to the right Python type for the block config."""
    if kind == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0
    return raw or ""


class HomepageBuilderView(MadgaStudioMixin, View):
    template_name = "madga/studio/homepage.html"

    def _render(self, request, site):
        blocks = list(
            HomepageBlock.objects.filter(site=site)
            if site
            else HomepageBlock.objects.none()
        )
        rows = []
        for idx, b in enumerate(blocks):
            rows.append(
                {
                    "obj": b,
                    "fields": [
                        {
                            "name": fname,
                            "label": flabel,
                            "kind": fkind,
                            "value": (b.config or {}).get(fname, ""),
                        }
                        for (fname, flabel, fkind) in BLOCK_FIELDS.get(b.block_type, [])
                    ],
                    "description": BLOCK_DESCRIPTIONS.get(b.block_type, ""),
                    "is_first": idx == 0,
                    "is_last": idx == len(blocks) - 1,
                }
            )
        return render(
            request,
            self.template_name,
            {
                "blocks": rows,
                "block_type_choices": HomepageBlock.BLOCK_TYPE_CHOICES,
                "block_descriptions": BLOCK_DESCRIPTIONS,
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
            block = get_object_or_404(HomepageBlock.objects.filter(site=site), pk=pk)
            # Preserve unknown keys (so power-users editing via API don't lose data).
            new_config = dict(block.config or {})
            for fname, _flabel, fkind in BLOCK_FIELDS.get(block.block_type, []):
                new_config[fname] = _coerce(fkind, request.POST.get(fname, ""))
            block.config = new_config
            block.is_visible = request.POST.get("is_visible") == "on"
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

        elif action in ("move_up", "move_down"):
            pk = request.POST.get("pk")
            block = HomepageBlock.objects.filter(site=site, pk=pk).first()
            if block:
                ordered = list(
                    HomepageBlock.objects.filter(site=site).order_by("sort_order", "id")
                )
                idx = next(
                    (i for i, b in enumerate(ordered) if b.pk == block.pk), None
                )
                if idx is not None:
                    swap = idx - 1 if action == "move_up" else idx + 1
                    if 0 <= swap < len(ordered):
                        with transaction.atomic():
                            a, b = ordered[idx], ordered[swap]
                            a.sort_order, b.sort_order = b.sort_order, a.sort_order
                            a.save(update_fields=["sort_order"])
                            b.save(update_fields=["sort_order"])

        return redirect("madga_studio:homepage_builder")
