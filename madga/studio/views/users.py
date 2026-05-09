"""Studio Users + invitations."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from madga.models import SiteUser, UserInvitation

from ..mixins import MadgaStudioMixin


class UserListView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/users.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        if site:
            ctx["memberships"] = (
                SiteUser.objects.filter(site=site).select_related("user")
            )
            ctx["invitations"] = UserInvitation.objects.filter(
                site=site, status=UserInvitation.STATUS_PENDING
            )
        else:
            ctx["memberships"] = []
            ctx["invitations"] = []
        ctx["roles"] = SiteUser.ROLE_CHOICES
        return ctx


class UserInviteView(MadgaStudioMixin, View):
    def post(self, request):
        if not self.has_perm("manage_users"):
            messages.error(request, "No tienes permiso para invitar usuarios.")
            return redirect("madga_studio:user_list")
        site = self.get_site()
        email = (request.POST.get("email") or "").strip().lower()
        role = request.POST.get("role") or SiteUser.ROLE_AUTHOR
        if not email:
            messages.error(request, "Email requerido.")
            return redirect("madga_studio:user_list")
        UserInvitation.objects.update_or_create(
            site=site,
            email=email,
            defaults={
                "role": role,
                "invited_by": request.user,
                "status": UserInvitation.STATUS_PENDING,
            },
        )
        messages.success(request, f"Invitación enviada a {email}.")
        return redirect("madga_studio:user_list")


class UserRoleUpdateView(MadgaStudioMixin, View):
    def post(self, request, pk):
        if not self.has_perm("manage_users"):
            messages.error(request, "Permiso denegado.")
            return redirect("madga_studio:user_list")
        membership = get_object_or_404(
            SiteUser.objects.filter(site=self.get_site()), pk=pk
        )
        role = request.POST.get("role")
        if role in dict(SiteUser.ROLE_CHOICES):
            membership.role = role
            membership.save(update_fields=["role"])
            messages.success(request, "Rol actualizado.")
        return redirect("madga_studio:user_list")
