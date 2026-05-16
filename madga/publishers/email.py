"""Email subscribers publisher — built-in, uses Django's email backend."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .base import Publisher, PublishResult, register_publisher


@register_publisher
class EmailSubscribersPublisher(Publisher):
    key = "email_subscribers"
    label = _("Email subscribers")
    description = _(
        "Send the broadcast as an email to every active subscriber of this site. "
        "Uses your project's configured EMAIL_BACKEND."
    )
    icon = "mail"

    def is_configured(self) -> bool:
        # Django always has an email backend (console/locmem in dev). We never
        # block this publisher — projects in dev can still try it and see the
        # rendered emails in the console.
        return True

    def estimate_targets(self, job) -> int:
        from madga.models import Subscriber
        return Subscriber.objects.filter(site=job.site, is_active=True).count()

    def publish(self, job) -> PublishResult:
        from madga.models import Subscriber

        result = PublishResult()
        qs = Subscriber.objects.filter(site=job.site, is_active=True).iterator()

        for subscriber in qs:
            try:
                self._send_one(job, subscriber)
                result.sent += 1
            except Exception as e:  # noqa: BLE001 - report every failure, don't abort
                result.failed += 1
                result.errors.append({
                    "target": subscriber.email,
                    "msg": str(e),
                })
        return result

    def _send_one(self, job, subscriber):
        unsubscribe_url = self._unsubscribe_url(job, subscriber)
        ctx = {
            "job": job,
            "site": job.site,
            "subscriber": subscriber,
            "subject": job.subject,
            "body_html": job.body_html,
            "body_text": job.body_text,
            "related_url": job.related_url,
            "unsubscribe_url": unsubscribe_url,
        }
        text_body = render_to_string("madga/emails/broadcast.txt", ctx)
        html_body = render_to_string("madga/emails/broadcast.html", ctx)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
        msg = EmailMultiAlternatives(
            subject=job.subject,
            body=text_body,
            from_email=from_email,
            to=[subscriber.email],
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

    def _unsubscribe_url(self, job, subscriber) -> str:
        # Best-effort absolute URL. If the site has a domain set we use it;
        # otherwise we return a relative path the host project can prepend to.
        path = reverse(
            "madga_unsubscribe",
            kwargs={"token": subscriber.unsubscribe_token},
        )
        domain = (job.site.domain or "").strip()
        if domain and not domain.startswith("http"):
            scheme = "https" if domain != "localhost" else "http"
            return f"{scheme}://{domain}{path}"
        return path
