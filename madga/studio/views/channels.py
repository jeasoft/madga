"""Studio Channels page: connect/disconnect/pause publisher accounts."""

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


class ChannelListView(MadgaStudioMixin, View):
    """Lists every account-driven publisher + its current connections."""

    template_name = "madga/studio/channels.html"

    def get(self, request):
        site = self.get_site()

        publishers = [p for p in all_publishers() if p.credential_fields]
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
            },
        )


class ChannelConnectView(MadgaStudioMixin, View):
    """Manual token-paste connect flow (no OAuth yet)."""

    template_name = "madga/studio/channel_connect.html"

    def get(self, request, key):
        publisher = get_publisher(key)
        if publisher is None or not publisher.credential_fields:
            return HttpResponseBadRequest(_("Unknown channel."))
        return render(request, self.template_name, {"publisher": publisher})

    def post(self, request, key):
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))
        publisher = get_publisher(key)
        if publisher is None or not publisher.credential_fields:
            return HttpResponseBadRequest(_("Unknown channel."))

        handle = (request.POST.get("handle") or "").strip()
        display_name = (request.POST.get("display_name") or handle).strip()

        creds = {}
        for f in publisher.credential_fields:
            creds[f.name] = (request.POST.get(f.name) or "").strip()

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
