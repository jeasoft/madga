"""Workspace switcher + self-service workspace creation."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import View

from madga.models import Site, SiteUser

from ..mixins import MadgaStudioMixin


def _user_sites(user):
    """All Sites the given user can access (superuser sees them all)."""
    if user.is_superuser:
        return Site.objects.filter(is_active=True).order_by("name")
    return Site.objects.filter(
        is_active=True,
        memberships__user=user,
    ).distinct().order_by("name")


class WorkspaceSwitchView(MadgaStudioMixin, View):
    """Set the user's active Site for the studio session."""

    def post(self, request):
        site_id = request.POST.get("site_id")
        next_url = request.POST.get("next") or reverse("madga_studio:dashboard")

        if not site_id:
            return HttpResponseRedirect(next_url)

        site = get_object_or_404(Site, id=site_id, is_active=True)

        # Authorize the user to switch into this site.
        if not request.user.is_superuser:
            if not SiteUser.objects.filter(site=site, user=request.user).exists():
                messages.error(request, _("You don't belong to that workspace."))
                return HttpResponseRedirect(next_url)

        request.session["madga_active_site_id"] = str(site.id)
        messages.success(request, _("Switched to %(name)s.") % {"name": site.name})
        return HttpResponseRedirect(next_url)


class WorkspaceCreateView(MadgaStudioMixin, View):
    """Self-service: any authenticated user can spin up a new workspace.

    The creator becomes its Owner. The studio redirects there immediately.
    """

    template_name = "madga/studio/workspace_create.html"

    def get(self, request):
        return render(request, self.template_name, {})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        domain = (request.POST.get("domain") or "").strip()
        if not name:
            messages.error(request, _("Name is required."))
            return render(request, self.template_name, {})

        # If domain not provided, derive a placeholder from the name.
        if not domain:
            from slugify import slugify
            domain = f"{slugify(name)[:40]}.local"

        # Domain must be unique across MADGA sites.
        if Site.objects.filter(domain=domain).exists():
            messages.error(
                request,
                _("A workspace with domain '%(domain)s' already exists.") % {"domain": domain},
            )
            return render(request, self.template_name, {"name": name, "domain": domain})

        site = Site.objects.create(name=name, domain=domain)
        SiteUser.objects.create(site=site, user=request.user, role=SiteUser.ROLE_OWNER)
        request.session["madga_active_site_id"] = str(site.id)
        messages.success(request, _("Workspace '%(name)s' created.") % {"name": name})
        return HttpResponseRedirect(reverse("madga_studio:dashboard"))
