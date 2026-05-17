"""Public form-submission handler."""

from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from madga.models import FormSubmission, HomepageBlock


class FormSubmitView(View):
    """Accept a public form submission and create a ``FormSubmission`` row.

    The form's POST target is ``/madga/form/<block_id>/submit/``. We
    look up the HomepageBlock (or skip the lookup for inline forms if
    block_id doesn't match anything — useful for ad-hoc forms a host
    project renders without going through the registry), persist the
    submission, optionally email the configured recipient, and fire
    the ``form.submitted`` webhook.

    On success: redirect back to ``source`` (the page the form was
    on) with ``?submitted=<block_id>`` so the template can render the
    success message inline.
    """

    def post(self, request, block_id):
        # Honeypot: silently drop if filled
        if (request.POST.get("website") or "").strip():
            return JsonResponse({"ok": True})

        block = HomepageBlock.objects.filter(pk=block_id).select_related("site").first()
        site = block.site if block else None
        if site is None:
            # Allow ad-hoc forms by reading madga_site from request
            site = getattr(request, "madga_site", None)
        config = block.config if block else {}

        # Strip CSRF / system fields from the persisted data.
        skip = {"csrfmiddlewaretoken", "website", "source"}
        data = {k: v for k, v in request.POST.items() if k not in skip}

        sub = FormSubmission.objects.create(
            site=site,
            block_id=block_id,
            form_key=config.get("form_key") or "contact",
            source_url=request.POST.get("source", "")[:500],
            data=data,
            ip=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        # Notification email — best-effort, never block the response.
        recipient = (config.get("recipient_email") or "").strip()
        if recipient:
            try:
                _send_notification(sub, recipient, site)
            except Exception:  # noqa: BLE001
                pass

        # Webhook
        try:
            from madga.webhooks import fire_event
            fire_event(site, "form.submitted", {
                "id": str(sub.id),
                "block_id": str(block_id),
                "form_key": sub.form_key,
                "data": data,
                "source_url": sub.source_url,
            })
        except Exception:  # noqa: BLE001
            pass

        # JSON receivers (e.g. SPA front-ends) get a JSON ack.
        if request.headers.get("Accept", "").startswith("application/json") or \
           request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "id": str(sub.id)})

        source = request.POST.get("source", "/")
        sep = "&" if "?" in source else "?"
        return HttpResponseRedirect(f"{source}{sep}submitted={block_id}")


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _send_notification(submission, recipient: str, site) -> None:
    """Email the form recipient with the submission contents."""
    from django.conf import settings as dj_settings

    subject_prefix = f"[{site.name}] " if site else "[MADGA] "
    sender = (submission.data.get("email") or submission.data.get("name") or "anonymous")
    lines = [f"{k}: {v}" for k, v in (submission.data or {}).items()]
    body = (
        f"New {submission.form_key} submission.\n\n"
        + "\n".join(lines)
        + f"\n\nSource: {submission.source_url or '(unknown)'}\n"
        f"IP: {submission.ip or '?'}\n"
        f"At: {submission.created_at.isoformat()}\n"
    )

    EmailMessage(
        subject=f"{subject_prefix}{submission.form_key}: {sender}",
        body=body,
        from_email=getattr(dj_settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        to=[recipient],
    ).send(fail_silently=False)
