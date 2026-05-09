"""Studio navigation builder (v0.2)."""

from django.contrib import messages
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
            NavItem.objects.filter(site=site).select_related("parent")
            if site
            else NavItem.objects.none()
        )
        return render(
            request,
            self.template_name,
            {
                "items": items,
                "parent_choices": items.filter(parent__isnull=True),
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
            if not label or not url:
                messages.error(request, "Label y URL son obligatorios.")
                return redirect("madga_studio:navigation")
            parent_id = request.POST.get("parent") or None
            parent = (
                NavItem.objects.filter(site=site, pk=parent_id).first()
                if parent_id
                else None
            )
            NavItem.objects.create(
                site=site,
                label=label,
                url=url,
                parent=parent,
                sort_order=int(request.POST.get("sort_order") or 0),
                open_in_new_tab=bool(request.POST.get("open_in_new_tab")),
            )
            messages.success(request, "Item de navegación creado.")

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

        return redirect("madga_studio:navigation")
