"""Studio navigation builder."""

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from madga.models import NavItem

from ..mixins import MadgaStudioMixin


class NavigationView(MadgaStudioMixin, View):
    """List + inline editor for a Site's navigation items.

    All mutations (create/update/delete) flow through a single POST handler
    discriminated by the ``action`` form field. Sort order is edited as a
    plain integer — drag-to-reorder was skipped to keep the JS surface small.
    """

    template_name = "madga/studio/navigation.html"

    def _render(self, request, site):
        items = (
            NavItem.objects.filter(site=site).select_related("parent").prefetch_related("children")
            if site
            else NavItem.objects.none()
        )
        # Footer columns: parent items with location=footer.
        footer_columns = items.filter(
            location=NavItem.LOCATION_FOOTER, parent__isnull=True
        )
        return render(
            request,
            self.template_name,
            {
                "items": items,
                "footer_columns": footer_columns,
                "site": site,
                "membership": self.get_membership(),
            },
        )

    def get(self, request):
        return self._render(request, self.get_site())

    def post(self, request):
        if not self.has_perm("manage_settings"):
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:navigation")
        site = self.get_site()
        if site is None:
            messages.error(request, "No hay site activo.")
            return redirect("madga_studio:navigation")

        action = request.POST.get("action") or "create"

        if action == "create":
            label = (request.POST.get("label") or "").strip()
            url = (request.POST.get("url") or "").strip()
            location = request.POST.get("location") or NavItem.LOCATION_HEADER
            parent_id = request.POST.get("parent") or None
            parent = (
                NavItem.objects.filter(site=site, pk=parent_id).first()
                if parent_id
                else None
            )
            # Footer column TITLES (no parent, location=footer) don't need a URL;
            # everything else does.
            requires_url = not (location == NavItem.LOCATION_FOOTER and parent is None)
            if not label or (requires_url and not url):
                messages.error(request, "Label y URL son obligatorios.")
                return redirect("madga_studio:navigation")
            NavItem.objects.create(
                site=site,
                label=label,
                url=url,
                location=location,
                parent=parent,
                sort_order=int(request.POST.get("sort_order") or 0),
                open_in_new_tab=bool(request.POST.get("open_in_new_tab")),
            )
            messages.success(request, "Item creado.")

        elif action == "update":
            pk = request.POST.get("pk")
            item = get_object_or_404(NavItem.objects.filter(site=site), pk=pk)
            item.label = (request.POST.get("label") or item.label).strip()
            item.url = (request.POST.get("url") or item.url).strip()
            parent_id = request.POST.get("parent") or None
            if parent_id and str(parent_id) != str(item.pk):
                item.parent = NavItem.objects.filter(
                    site=site, pk=parent_id
                ).first()
            else:
                item.parent = None
            try:
                item.sort_order = int(request.POST.get("sort_order") or 0)
            except ValueError:
                pass
            item.open_in_new_tab = bool(request.POST.get("open_in_new_tab"))
            item.save()
            messages.success(request, "Item actualizado.")

        elif action == "delete":
            pk = request.POST.get("pk")
            NavItem.objects.filter(site=site, pk=pk).delete()
            messages.success(request, "Item eliminado.")

        elif action == "reorder":
            ids = request.POST.getlist("ids[]") or request.POST.getlist("ids")
            if ids:
                rows = {
                    str(i.pk): i
                    for i in NavItem.objects.filter(site=site, pk__in=ids)
                }
                with transaction.atomic():
                    for new_order, pk in enumerate(ids, start=1):
                        item = rows.get(str(pk))
                        if item and item.sort_order != new_order:
                            item.sort_order = new_order
                            item.save(update_fields=["sort_order"])
            return JsonResponse({"ok": True})

        return redirect("madga_studio:navigation")
