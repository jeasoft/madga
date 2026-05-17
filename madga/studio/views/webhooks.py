"""Studio views for webhooks: list, create, edit, test, deliveries."""

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, View

from madga.models import REGISTERED_EVENTS, WebhookDelivery, WebhookEndpoint
from madga.webhooks import _deliver_one, fire_event

from ..mixins import MadgaStudioMixin


class WebhookListView(MadgaStudioMixin, ListView):
    template_name = "madga/studio/webhooks.html"
    paginate_by = 50
    context_object_name = "endpoints"

    def get_queryset(self):
        site = self.get_site()
        if site is None:
            return WebhookEndpoint.objects.none()
        return WebhookEndpoint.objects.filter(site=site)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["events"] = REGISTERED_EVENTS
        site = self.get_site()
        if site:
            ctx["recent_deliveries"] = (
                WebhookDelivery.objects.filter(endpoint__site=site)
                .select_related("endpoint")
                .order_by("-created_at")[:20]
            )
        else:
            ctx["recent_deliveries"] = []
        return ctx


class WebhookCreateView(MadgaStudioMixin, View):
    template_name = "madga/studio/webhook_form.html"

    def get(self, request, pk=None):
        site = self.get_site()
        endpoint = None
        if pk:
            endpoint = get_object_or_404(WebhookEndpoint, pk=pk, site=site)
        return render(request, self.template_name, {
            "endpoint": endpoint,
            "events": REGISTERED_EVENTS,
        })

    def post(self, request, pk=None):
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))
        endpoint = None
        if pk:
            endpoint = get_object_or_404(WebhookEndpoint, pk=pk, site=site)

        label = (request.POST.get("label") or "").strip()
        url = (request.POST.get("url") or "").strip()
        events = request.POST.getlist("events")
        is_active = request.POST.get("is_active") == "on"

        if not url:
            messages.error(request, _("URL is required."))
            return render(request, self.template_name, {
                "endpoint": endpoint, "events": REGISTERED_EVENTS,
                "form_url": url, "form_label": label, "form_events": events,
            })

        if endpoint is None:
            endpoint = WebhookEndpoint.objects.create(
                site=site, url=url, label=label, events=events,
                is_active=is_active, created_by=request.user,
            )
            messages.success(request, _("Webhook endpoint created."))
        else:
            endpoint.url = url
            endpoint.label = label
            endpoint.events = events
            endpoint.is_active = is_active
            endpoint.save()
            messages.success(request, _("Webhook endpoint updated."))
        return HttpResponseRedirect(reverse("madga_studio:webhook_list"))


class WebhookDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        endpoint = get_object_or_404(
            WebhookEndpoint, pk=pk, site=self.get_site()
        )
        endpoint.delete()
        messages.success(request, _("Webhook endpoint removed."))
        return HttpResponseRedirect(reverse("madga_studio:webhook_list"))


class WebhookRotateSecretView(MadgaStudioMixin, View):
    def post(self, request, pk):
        endpoint = get_object_or_404(
            WebhookEndpoint, pk=pk, site=self.get_site()
        )
        endpoint.rotate_secret()
        messages.success(
            request,
            _("New secret generated. Update your receiver to use it."),
        )
        return HttpResponseRedirect(reverse("madga_studio:webhook_list"))


class WebhookTestView(MadgaStudioMixin, View):
    """Fire a ``test.ping`` event to this endpoint and run delivery sync."""

    def post(self, request, pk):
        endpoint = get_object_or_404(
            WebhookEndpoint, pk=pk, site=self.get_site()
        )
        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event="test.ping",
            payload={"message": "MADGA webhook test", "sent_by": request.user.username},
            next_attempt_at=None,
        )
        ok = _deliver_one(delivery)
        if ok:
            messages.success(
                request,
                _("Test delivered (HTTP %(status)s).") % {"status": delivery.response_status},
            )
        else:
            messages.error(
                request,
                _("Test failed: %(err)s") % {"err": (delivery.error or "no response")[:200]},
            )
        return HttpResponseRedirect(reverse("madga_studio:webhook_list"))
