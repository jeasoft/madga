"""Studio CRUD for the current user's API keys."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View

from madga.models import UserApiKey

from ..mixins import MadgaStudioMixin


class UserApiKeyListView(MadgaStudioMixin, View):
    template_name = "madga/studio/api_keys.html"

    def get(self, request):
        return render(request, self.template_name, {
            "keys": UserApiKey.objects.filter(user=request.user),
            "site": self.get_site(),
            "membership": self.get_membership(),
            # Show the full key once, right after creation, via session flash.
            "new_key": request.session.pop("_madga_new_key", None),
            "new_key_label": request.session.pop("_madga_new_key_label", None),
        })

    def post(self, request):
        action = request.POST.get("action") or "create"

        if action == "create":
            label = (request.POST.get("label") or "").strip() or "Untitled key"
            site_pk = request.POST.get("site") or None
            site = self.get_site() if site_pk else None
            key = UserApiKey.objects.create(
                user=request.user,
                site=site if site_pk else None,
                label=label,
            )
            # Flash the full key — visible exactly once on next page load.
            request.session["_madga_new_key"] = key.key
            request.session["_madga_new_key_label"] = key.label
            messages.success(request, _("API key created. Copy it now — won't be shown again."))

        elif action == "revoke":
            pk = request.POST.get("pk")
            uk = get_object_or_404(
                UserApiKey.objects.filter(user=request.user), pk=pk
            )
            uk.is_active = False
            uk.save(update_fields=["is_active", "updated_at"])
            messages.success(request, _("API key revoked."))

        elif action == "delete":
            pk = request.POST.get("pk")
            UserApiKey.objects.filter(user=request.user, pk=pk).delete()
            messages.success(request, _("API key deleted."))

        elif action == "rotate":
            pk = request.POST.get("pk")
            uk = get_object_or_404(
                UserApiKey.objects.filter(user=request.user), pk=pk
            )
            new_key = uk.rotate()
            request.session["_madga_new_key"] = new_key
            request.session["_madga_new_key_label"] = uk.label
            messages.success(request, _("API key rotated. Copy the new value."))

        return redirect("madga_studio:api_keys")
