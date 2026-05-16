"""Public broadcast endpoints: unsubscribe + double-opt-in confirm."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from madga.models import Subscriber


class UnsubscribeView(View):
    """One-click unsubscribe handler reachable from ``List-Unsubscribe`` headers.

    Accepts both POST (RFC 8058 one-click) and GET (legacy email-client
    fallback). On success, marks the subscriber inactive and renders a
    minimal confirmation page.
    """

    template_name = "madga/broadcast/unsubscribed.html"

    def get(self, request, token):
        return self._handle(request, token)

    def post(self, request, token):
        return self._handle(request, token)

    def _handle(self, request, token):
        subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)
        if subscriber.is_active:
            subscriber.unsubscribe()
        return render(
            request,
            self.template_name,
            {"subscriber": subscriber, "site": subscriber.site},
        )
