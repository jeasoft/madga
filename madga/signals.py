"""MADGA signals.

- ``pre_save`` on Post/Page: auto-slug + body_html caching.
- ``user_post_signup``: custom signal fired after a brand-new user signs up
  via the public flow. Host projects subscribe to create their profile
  rows (e.g. TalentProfile, CompanyProfile). Args:
    sender:   the User model class
    user:     the newly-created User instance
    request:  the HttpRequest that triggered signup (may be None for
              shell/management invocations)
    kind:     optional string for multi-type onboarding ("talent",
              "company", …) — set in session by the pre-signup picker
              and copied into the signal so listeners can branch.

Usage::

    # myapp/signals.py
    from django.dispatch import receiver
    from madga.signals import user_post_signup

    @receiver(user_post_signup)
    def create_profile(sender, user, request, kind, **kw):
        if kind == "talent":
            TalentProfile.objects.create(user=user)
        elif kind == "company":
            CompanyProfile.objects.create(user=user)
"""

from django.db.models.signals import pre_save
from django.dispatch import Signal, receiver
from slugify import slugify

from madga.models import Page, Post
from madga.renderer import render_blocks


user_post_signup = Signal()


def _unique_slug(model, base: str, instance) -> str:
    candidate = base or "post"
    n = 1
    qs = model.objects.exclude(pk=instance.pk) if instance.pk else model.objects.all()
    while qs.filter(slug=candidate).exists():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


@receiver(pre_save, sender=Post)
def post_pre_save(sender, instance: Post, **kwargs):
    if not instance.slug:
        instance.slug = _unique_slug(Post, slugify(instance.title)[:480], instance)
    instance.body_html = render_blocks(instance.body)


@receiver(pre_save, sender=Page)
def page_pre_save(sender, instance: Page, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)[:480]
    instance.body_html = render_blocks(instance.body)


# Bridge from allauth's user_signed_up → our user_post_signup, copying the
# `madga_signup_kind` session var (set by the pre-signup type-picker if the
# host project uses one) into the signal.
try:
    from allauth.account.signals import user_signed_up
except ImportError:  # allauth optional at import time
    user_signed_up = None


def _on_allauth_user_signed_up(sender, request, user, **kwargs):
    kind = ""
    if request is not None and hasattr(request, "session"):
        kind = request.session.pop("madga_signup_kind", "") or ""
    user_post_signup.send(
        sender=user.__class__,
        user=user,
        request=request,
        kind=kind,
    )


if user_signed_up is not None:
    user_signed_up.connect(_on_allauth_user_signed_up)
