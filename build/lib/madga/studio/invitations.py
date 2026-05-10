"""Invitation email sending.

Uses Django's standard email machinery. Default ``EMAIL_BACKEND`` in dev is
``django.core.mail.backends.console.EmailBackend`` which prints emails to the
runserver console — safe for testing without leaking real mail.
"""

from __future__ import annotations

import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

log = logging.getLogger("madga.invitations")


def send_invitation_email(invitation, request=None) -> bool:
    """Send an invitation email. Returns True on success.

    Errors log a warning but don't raise — the caller probably wants the
    invitation row created either way and can resend later.
    """
    site = invitation.site
    accept_path = reverse("madga_studio:accept_invite", kwargs={"token": invitation.token})
    accept_url = (
        request.build_absolute_uri(accept_path)
        if request is not None
        else f"https://{site.domain}{accept_path}"
    )
    subject = f"Te invitaron a {site.name}"
    ctx = {
        "invitation": invitation,
        "site": site,
        "accept_url": accept_url,
    }
    body_text = render_to_string("madga/emails/invitation.txt", ctx)
    body_html = render_to_string("madga/emails/invitation.html", ctx)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            to=[invitation.email],
        )
        msg.attach_alternative(body_html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception as exc:  # noqa: BLE001 — we want the message in logs
        log.warning("Failed to send invitation email to %s: %s", invitation.email, exc)
        return False
