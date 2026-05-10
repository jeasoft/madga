"""Studio Users + invitations."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from madga.models import SiteUser, UserInvitation

from ..mixins import MadgaStudioMixin
from ..invitations import send_invitation_email


INVITE_TTL_DAYS = 14


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
            messages.error(request, _("No tienes permiso para invitar usuarios."))
            return redirect("madga_studio:user_list")
        site = self.get_site()
        email = (request.POST.get("email") or "").strip().lower()
        role = request.POST.get("role") or SiteUser.ROLE_AUTHOR
        if not email:
            messages.error(request, _("Email requerido."))
            return redirect("madga_studio:user_list")
        invitation, created = UserInvitation.objects.update_or_create(
            site=site,
            email=email,
            defaults={
                "role": role,
                "invited_by": request.user,
                "status": UserInvitation.STATUS_PENDING,
            },
        )
        # Send the email (default Django EMAIL_BACKEND is console, so no real
        # mail leaves dev). Errors are logged but don't break the flow.
        sent = send_invitation_email(invitation, request)
        if sent:
            messages.success(request, f"Invitación enviada a {email}.")
        else:
            messages.warning(
                request,
                f"Invitación creada para {email}, pero el envío de email falló. "
                f"Compártele el enlace manualmente desde la lista.",
            )
        return redirect("madga_studio:user_list")


class AcceptInviteView(View):
    """Public endpoint for invitees: GET shows accept-or-cancel; POST creates
    SiteUser membership and (if needed) the User account."""

    template_name = "madga/studio/accept_invite.html"

    def _resolve(self, token):
        return UserInvitation.objects.filter(
            token=token,
            status=UserInvitation.STATUS_PENDING,
        ).select_related("site").first()

    def _is_expired(self, inv):
        return inv.created_at < timezone.now() - timedelta(days=INVITE_TTL_DAYS)

    def get(self, request, token):
        inv = self._resolve(token)
        if inv is None:
            return render(request, self.template_name, {"invitation": None, "error": "not-found"})
        if self._is_expired(inv):
            inv.status = UserInvitation.STATUS_EXPIRED
            inv.save(update_fields=["status"])
            return render(request, self.template_name, {"invitation": inv, "error": "expired"})
        return render(request, self.template_name, {"invitation": inv, "error": None})

    def post(self, request, token):
        inv = self._resolve(token)
        if inv is None or self._is_expired(inv):
            messages.error(request, _("Esta invitación ya no es válida."))
            return redirect("madga_studio:login")

        User = get_user_model()
        # If the visitor is logged in with a matching email, just attach.
        # Otherwise create a brand-new user with the invited email + a temp
        # password (they reset on first login).
        if request.user.is_authenticated and (
            request.user.email or ""
        ).lower() == inv.email.lower():
            user = request.user
        else:
            user, created = User.objects.get_or_create(
                email=inv.email,
                defaults={"username": inv.email.split("@")[0][:30]},
            )
            if created:
                # Force a password reset flow: random unusable pw.
                user.set_unusable_password()
                user.save(update_fields=["password"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        SiteUser.objects.get_or_create(
            site=inv.site, user=user,
            defaults={"role": inv.role},
        )
        inv.status = UserInvitation.STATUS_ACCEPTED
        inv.accepted_at = timezone.now()
        inv.save(update_fields=["status", "accepted_at"])

        messages.success(
            request,
            f"Bienvenido a {inv.site.name}. Tu rol: {inv.get_role_display()}.",
        )
        return redirect("madga_studio:dashboard")


class UserRoleUpdateView(MadgaStudioMixin, View):
    def post(self, request, pk):
        if not self.has_perm("manage_users"):
            messages.error(request, _("Permiso denegado."))
            return redirect("madga_studio:user_list")
        membership = get_object_or_404(
            SiteUser.objects.filter(site=self.get_site()), pk=pk
        )
        role = request.POST.get("role")
        if role in dict(SiteUser.ROLE_CHOICES):
            membership.role = role
            membership.save(update_fields=["role"])
            messages.success(request, _("Rol actualizado."))
        return redirect("madga_studio:user_list")
