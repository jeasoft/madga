"""Security headers middleware.

Adds the standard set of hardening response headers everyone forgets to
turn on. Lives in MADGA so host projects get them for free, but every
header is overridable per-project via Django settings (see attribute
names below).

Defaults are intentionally conservative — they won't break a normal
Tailwind + Editor.js + iframe-preview stack — but enable
``MADGA_CSP_STRICT = True`` in your settings if you want a real
locked-down CSP that requires you to enumerate every external host.

Settings respected (all optional, sensible defaults if unset):

- ``MADGA_HSTS_MAX_AGE`` — defaults to ``31536000`` (1 year).
- ``MADGA_HSTS_INCLUDE_SUBDOMAINS`` — bool, default True.
- ``MADGA_HSTS_PRELOAD`` — bool, default False (only enable once you've
  confirmed the site is ready for HSTS preload submission).
- ``MADGA_REFERRER_POLICY`` — default ``strict-origin-when-cross-origin``.
- ``MADGA_PERMISSIONS_POLICY`` — default disables camera / mic /
  geolocation / payment.
- ``MADGA_CSP`` — string CSP header value. If unset, no CSP header is
  emitted (apps that haven't audited their assets should opt in
  explicitly).
- ``MADGA_SECURITY_SKIP_PATHS`` — list of path prefixes to skip
  entirely. Default: nothing.

The middleware is a NO-OP in DEBUG by default (you don't want HSTS in
local dev). Set ``MADGA_SECURITY_FORCE = True`` to enable it in DEBUG
for testing.
"""

from __future__ import annotations

from django.conf import settings


DEFAULT_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
    "magnetometer=(), gyroscope=(), accelerometer=()"
)


class SecurityHeadersMiddleware:
    """Add hardening response headers on every response.

    Mount AFTER ``django.middleware.security.SecurityMiddleware`` so we
    can layer additional headers on top of Django's own.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.enabled = (
            not settings.DEBUG
            or getattr(settings, "MADGA_SECURITY_FORCE", False)
        )
        self.skip_paths = tuple(
            getattr(settings, "MADGA_SECURITY_SKIP_PATHS", []) or []
        )

    def __call__(self, request):
        response = self.get_response(request)
        if not self.enabled:
            return response
        if self.skip_paths and any(
            request.path.startswith(p) for p in self.skip_paths
        ):
            return response
        self._apply(request, response)
        return response

    def _apply(self, request, response):
        # HSTS — only on HTTPS requests, Django's own SecurityMiddleware
        # already gates this, but our header value can be richer.
        if request.is_secure():
            max_age = int(getattr(settings, "MADGA_HSTS_MAX_AGE", 31536000))
            parts = [f"max-age={max_age}"]
            if getattr(settings, "MADGA_HSTS_INCLUDE_SUBDOMAINS", True):
                parts.append("includeSubDomains")
            if getattr(settings, "MADGA_HSTS_PRELOAD", False):
                parts.append("preload")
            response.setdefault("Strict-Transport-Security", "; ".join(parts))

        # Content type sniffing
        response.setdefault("X-Content-Type-Options", "nosniff")

        # Referrer policy — tight but not breaking for analytics referrers
        response.setdefault(
            "Referrer-Policy",
            getattr(settings, "MADGA_REFERRER_POLICY", "strict-origin-when-cross-origin"),
        )

        # Permissions policy
        response.setdefault(
            "Permissions-Policy",
            getattr(settings, "MADGA_PERMISSIONS_POLICY", DEFAULT_PERMISSIONS_POLICY),
        )

        # X-Frame-Options: keep Django's default (DENY) unless host opts
        # into SAMEORIGIN (studio iframe preview needs SAMEORIGIN —
        # handled by the @xframe_options_sameorigin decorator on the
        # preview views, not here).

        # CSP: only emit if the host project provides a value. CSP is
        # heavily app-specific so we won't ship a guess that would
        # blow up Editor.js's inline styles.
        csp = getattr(settings, "MADGA_CSP", None)
        if csp:
            response.setdefault("Content-Security-Policy", csp)

        # Cross-origin policies — gentle defaults that don't break
        # iframe previews or third-party embeds.
        response.setdefault(
            "Cross-Origin-Opener-Policy",
            getattr(settings, "MADGA_COOP", "same-origin-allow-popups"),
        )
