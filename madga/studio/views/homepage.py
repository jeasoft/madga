"""Studio homepage blocks builder — registry-driven.

Block types are declared by registering BlockType subclasses (see
madga/blocks/builtin.py for the defaults; sites/themes register their own
in their AppConfig.ready()).

The view reads the registry to build the "add a block" tray, render each
block's form (field-by-field via field.render_input()), and parse the
config out of POST data via field.coerce_from_post().
"""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from madga.blocks import all_block_types, get_block_type
from madga.models import HomepageBlock

from ..mixins import MadgaStudioMixin


class HomepageBuilderView(MadgaStudioMixin, View):
    template_name = "madga/studio/homepage.html"

    def _render(self, request, site):
        blocks = list(
            HomepageBlock.objects.filter(site=site).order_by("sort_order", "id")
            if site
            else HomepageBlock.objects.none()
        )
        rows = []
        for idx, b in enumerate(blocks):
            bt = get_block_type(b.block_type)
            if bt is None:
                # Unknown type: show a stripped row so the user can delete it
                # but not edit it. This keeps stale rows visible after removing
                # a block-type registration.
                rows.append({
                    "obj": b, "type": None, "fields_html": [],
                    "is_first": idx == 0, "is_last": idx == len(blocks) - 1,
                    "label": b.block_type, "description": "(tipo no registrado)",
                })
                continue
            cfg = b.config or {}
            fields_html = [
                {
                    "label": f.label,
                    "help_text": f.help_text,
                    "html": f.render_input(cfg.get(f.name, f.default_value()), prefix=""),
                }
                for f in bt.fields
            ]
            rows.append({
                "obj": b, "type": bt, "fields_html": fields_html,
                "label": bt.label, "description": bt.description,
                "is_first": idx == 0, "is_last": idx == len(blocks) - 1,
            })

        return render(
            request,
            self.template_name,
            {
                "blocks": rows,
                "block_types": all_block_types(),
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
            block_type_key = request.POST.get("block_type")
            bt = get_block_type(block_type_key)
            if bt is None:
                messages.error(request, "Tipo de bloque inválido.")
                return redirect("madga_studio:homepage_builder")
            next_order = HomepageBlock.objects.filter(site=site).count() + 1
            HomepageBlock.objects.create(
                site=site,
                block_type=block_type_key,
                config=bt.default_config(),
                sort_order=next_order,
            )
            messages.success(request, f"Bloque '{bt.label}' añadido.")

        elif action == "update":
            pk = request.POST.get("pk")
            block = get_object_or_404(HomepageBlock.objects.filter(site=site), pk=pk)
            bt = get_block_type(block.block_type)
            if bt is None:
                messages.error(request, "Este tipo de bloque ya no existe.")
                return redirect("madga_studio:homepage_builder")
            # Preserve unknown keys (so future fields don't lose data).
            new_cfg = dict(block.config or {})
            new_cfg.update(bt.coerce_from_post(request.POST))
            block.config = new_cfg
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

        elif action == "reorder":
            # Drag-and-drop: ids[] is the new order. Persist sort_order = index+1.
            from django.http import JsonResponse

            ids = request.POST.getlist("ids[]") or request.POST.getlist("ids")
            if ids:
                blocks = {
                    str(b.pk): b
                    for b in HomepageBlock.objects.filter(site=site, pk__in=ids)
                }
                with transaction.atomic():
                    for new_order, pk in enumerate(ids, start=1):
                        b = blocks.get(str(pk))
                        if b and b.sort_order != new_order:
                            b.sort_order = new_order
                            b.save(update_fields=["sort_order"])
            return JsonResponse({"ok": True})

        return redirect("madga_studio:homepage_builder")
