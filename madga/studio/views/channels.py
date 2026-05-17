"""Studio Channels page: connect/disconnect/pause publisher accounts."""

import secrets

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import View

from madga.models import BroadcastJob, PublisherAccount
from madga.publishers import all_publishers, get_publisher

from ..mixins import MadgaStudioMixin


def _oauth_redirect_uri(request, key: str) -> str:
    """Absolute URL where the platform should send the user after consent."""
    path = reverse("madga_studio:channel_oauth_callback", kwargs={"key": key})
    return request.build_absolute_uri(path)


class ChannelListView(MadgaStudioMixin, View):
    """Lists every account-driven publisher + its current connections."""

    template_name = "madga/studio/channels.html"

    def get(self, request):
        site = self.get_site()

        publishers = [
            p for p in all_publishers()
            if p.credential_fields or p.oauth_supported
        ]
        # Surface OAuth publishers that still need MADGA_OAUTH config so
        # the card can show a "Needs setup" badge instead of failing
        # after the user clicks Connect. Check per-Site override first
        # (BYOA), then fall back to the global config.
        needs_oauth_config: set[str] = set()
        for p in publishers:
            if p.oauth_supported and p.oauth_client_credentials(site=site) is None:
                needs_oauth_config.add(p.key)

        # Which publishers have a per-Site BYOA app override active?
        from madga.models import SiteOAuthApp
        byoa_keys = set(
            SiteOAuthApp.objects.filter(site=site).values_list("publisher_key", flat=True)
            if site else []
        )

        accounts = (
            list(PublisherAccount.objects.filter(site=site)) if site else []
        )
        accounts_by_key: dict[str, list[PublisherAccount]] = {}
        for acct in accounts:
            accounts_by_key.setdefault(acct.publisher_key, []).append(acct)

        # Stats
        connected_count = sum(1 for a in accounts if a.is_active)
        last_30d = timezone.now() - timezone.timedelta(days=30)
        last_7d = timezone.now() - timezone.timedelta(days=7)
        if site:
            broadcasts_7d = BroadcastJob.objects.filter(
                site=site, created_at__gte=last_7d,
            ).count()
            in_queue = BroadcastJob.objects.filter(
                site=site, status=BroadcastJob.STATUS_PENDING,
            ).count()
            total_reach = sum(a.audience_size for a in accounts if a.is_active)
        else:
            broadcasts_7d = 0
            in_queue = 0
            total_reach = 0

        return render(
            request, self.template_name,
            {
                "publishers": publishers,
                "accounts_by_key": accounts_by_key,
                "supported_count": len(publishers),
                "connected_count": connected_count,
                "broadcasts_7d": broadcasts_7d,
                "in_queue": in_queue,
                "total_reach": total_reach,
                "needs_oauth_config": needs_oauth_config,
                "byoa_keys": byoa_keys,
            },
        )


class ChannelConnectView(MadgaStudioMixin, View):
    """Connect flow dispatcher.

    OAuth-supported publishers redirect to the platform's consent
    URL. Manual publishers render the token-paste form.
    """

    template_name = "madga/studio/channel_connect.html"

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None:
            return HttpResponseBadRequest(_("Unknown channel."))
        if publisher.oauth_supported:
            return HttpResponseRedirect(
                reverse("madga_studio:channel_oauth_start", kwargs={"key": key})
            )
        if not publisher.credential_fields:
            return HttpResponseBadRequest(_("This channel can't be connected from the UI."))
        return render(request, self.template_name, {"publisher": publisher})

    def post(self, request, key):
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))
        publisher = get_publisher(key)
        if publisher is None or not publisher.credential_fields or publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown channel."))

        creds = {}
        for f in publisher.credential_fields:
            creds[f.name] = (request.POST.get(f.name) or "").strip()

        # The "handle" we display in the studio comes either from the
        # publisher's credential schema (Bluesky) or from an explicit
        # studio-level field (Twitter, LinkedIn, ...).
        if publisher.has_handle_credential:
            handle = creds.get("handle", "")
        else:
            handle = (request.POST.get("handle") or "").strip()
        display_name = (request.POST.get("display_name") or handle).strip()

        account, created = PublisherAccount.objects.get_or_create(
            site=site, publisher_key=key, handle=handle,
            defaults={"display_name": display_name, "is_active": True},
        )
        account.display_name = display_name or account.display_name
        account.is_active = True
        account.last_error = ""
        account.set_credentials(creds)
        account.save()

        messages.success(
            request,
            _("Connected %(label)s as %(handle)s.") % {
                "label": publisher.label, "handle": handle or display_name,
            },
        )
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))


class ChannelToggleView(MadgaStudioMixin, View):
    def post(self, request, pk):
        site = self.get_site()
        account = get_object_or_404(PublisherAccount, pk=pk, site=site)
        if account.is_active:
            account.pause()
            messages.success(request, _("Channel paused."))
        else:
            account.resume()
            messages.success(request, _("Channel resumed."))
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))


class ChannelDisconnectView(MadgaStudioMixin, View):
    def post(self, request, pk):
        site = self.get_site()
        account = get_object_or_404(PublisherAccount, pk=pk, site=site)
        account.delete()
        messages.success(request, _("Channel disconnected."))
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))


class ChannelOAuthSetupView(MadgaStudioMixin, View):
    """Renders the platform-specific setup guide.

    Each OAuth publisher declares ``setup_instructions`` and
    ``setup_console_url``; this view picks the right one based on
    ``?key=twitter`` and renders the drawer-style help page with
    copy-paste-friendly chunks. The ``{CALLBACK}`` placeholder in the
    instruction bodies is replaced with the actual absolute callback
    URL for this deployment.
    """

    template_name = "madga/studio/oauth_setup.html"

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown OAuth channel."))

        callback = _oauth_redirect_uri(request, key)

        steps = []
        for step in publisher.setup_instructions or []:
            steps.append({
                "title": step.get("title", ""),
                "body": (step.get("body") or "").replace("{CALLBACK}", callback),
                "url": step.get("url", ""),
            })

        site = self.get_site()
        configured = publisher.oauth_client_credentials(site=site) is not None
        return render(request, self.template_name, {
            "publisher": publisher,
            "steps": steps,
            "callback_url": callback,
            "configured": configured,
        })


class ChannelOAuthStartView(MadgaStudioMixin, View):
    """Kick off an OAuth flow.

    Stores the PKCE verifier + state in session, then redirects to
    the platform's consent URL. The callback view validates the
    state and exchanges the code for tokens.
    """

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown OAuth channel."))
        site = self.get_site()
        if publisher.oauth_client_credentials(site=site) is None:
            messages.error(
                request,
                _("This channel needs an OAuth app — set MADGA_OAUTH['%(key)s'] "
                  "in settings (operator) or use 'Use my own app' for this workspace.")
                % {"key": key},
            )
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        state = secrets.token_urlsafe(24)
        pkce_verifier = secrets.token_urlsafe(48)
        request.session[f"madga_oauth_state_{key}"] = state
        request.session[f"madga_oauth_pkce_{key}"] = pkce_verifier

        redirect_uri = _oauth_redirect_uri(request, key)
        try:
            url = publisher.oauth_authorize_url(
                redirect_uri, state, pkce_verifier, site=site,
            )
        except RuntimeError as e:
            messages.error(request, str(e))
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))
        return HttpResponseRedirect(url)


class ChannelOAuthCallbackView(MadgaStudioMixin, View):
    """OAuth redirect target. Validates state, exchanges code, stores account."""

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown OAuth channel."))

        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))

        error = request.GET.get("error")
        if error:
            messages.error(request, _("OAuth was cancelled: %(err)s") % {"err": error})
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        code = request.GET.get("code")
        state = request.GET.get("state")
        expected_state = request.session.pop(f"madga_oauth_state_{key}", None)
        pkce_verifier = request.session.pop(f"madga_oauth_pkce_{key}", "")
        if not code or not state or state != expected_state:
            messages.error(request, _("OAuth state mismatch — please try again."))
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        redirect_uri = _oauth_redirect_uri(request, key)
        try:
            result = publisher.oauth_exchange(
                code, redirect_uri, pkce_verifier, site=site,
            )
        except Exception as e:  # noqa: BLE001
            messages.error(request, _("OAuth exchange failed: %(err)s") % {"err": str(e)[:200]})
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        handle = (result.get("handle") or "").strip()
        display_name = (result.get("display_name") or handle).strip()
        creds = result.get("credentials") or {}

        account, _created = PublisherAccount.objects.get_or_create(
            site=site, publisher_key=key, handle=handle,
            defaults={"display_name": display_name, "is_active": True},
        )
        account.display_name = display_name or account.display_name
        account.is_active = True
        account.last_error = ""
        account.set_credentials(creds)
        account.save()

        messages.success(
            request,
            _("Connected %(label)s as %(handle)s.") % {
                "label": publisher.label, "handle": handle or display_name,
            },
        )
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))


class ChannelTestView(MadgaStudioMixin, View):
    """Run :meth:`Publisher.test_connection` for a connected account.

    Stores the result on the account row (``last_error`` if it fails,
    cleared on success), and flashes a message back. Same redirect
    target as the other channel actions so the page shows the new
    state inline.
    """

    def post(self, request, pk):
        site = self.get_site()
        account = get_object_or_404(PublisherAccount, pk=pk, site=site)
        publisher = get_publisher(account.publisher_key)
        if publisher is None:
            messages.error(request, _("Publisher '%(key)s' is not registered.") % {"key": account.publisher_key})
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        ok, msg = publisher.test_connection(account)
        if ok:
            account.last_error = ""
            account.save(update_fields=["last_error"])
            messages.success(request, _("Test passed for %(handle)s: %(msg)s") % {
                "handle": account.handle or account.display_name or account.publisher_key,
                "msg": msg,
            })
        else:
            account.record_error(msg)
            messages.error(request, _("Test failed for %(handle)s: %(msg)s") % {
                "handle": account.handle or account.display_name or account.publisher_key,
                "msg": msg,
            })
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))


class ChannelByoaView(MadgaStudioMixin, View):
    """BYOA (Bring Your Own App): per-Site override of MADGA_OAUTH."""

    template_name = "madga/studio/channel_byoa.html"

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown OAuth channel."))
        site = self.get_site()
        from madga.models import SiteOAuthApp
        existing = (
            SiteOAuthApp.objects.filter(site=site, publisher_key=key).first()
            if site else None
        )
        callback = _oauth_redirect_uri(request, key)
        return render(request, self.template_name, {
            "publisher": publisher,
            "existing": existing,
            "callback_url": callback,
        })

    def post(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.oauth_supported:
            return HttpResponseBadRequest(_("Unknown OAuth channel."))
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))

        from madga.models import SiteOAuthApp
        client_id = (request.POST.get("client_id") or "").strip()
        client_secret = (request.POST.get("client_secret") or "").strip()
        notes = (request.POST.get("notes") or "").strip()

        if not client_id:
            SiteOAuthApp.objects.filter(site=site, publisher_key=key).delete()
            messages.success(
                request,
                _("Custom app removed — this channel now uses the global app."),
            )
            return HttpResponseRedirect(reverse("madga_studio:channel_list"))

        app, _created = SiteOAuthApp.objects.get_or_create(
            site=site, publisher_key=key,
            defaults={"client_id": client_id, "notes": notes},
        )
        app.client_id = client_id
        app.notes = notes
        if client_secret:
            app.set_secret(client_secret)
        app.save()
        messages.success(
            request,
            _("Custom %(label)s app saved.") % {"label": publisher.label},
        )
        return HttpResponseRedirect(reverse("madga_studio:channel_list"))
