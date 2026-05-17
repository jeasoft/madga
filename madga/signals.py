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

from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from slugify import slugify

from madga.models import MediaFile, Page, Post
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


@receiver(pre_save, sender=Post)
def post_pre_save_broadcast_trigger(sender, instance: Post, **kwargs):
    """Detect status transitions for the broadcast-on-publish flow.

    Stores the previous status on the instance so the post_save handler
    can compare. We can't read it AFTER save without an extra query, so
    we cache it here in a non-persistent attribute.
    """
    if not instance.pk:
        instance._madga_prev_status = None
        return
    try:
        prev = Post.objects.only("status").get(pk=instance.pk)
        instance._madga_prev_status = prev.status
    except Post.DoesNotExist:
        instance._madga_prev_status = None


@receiver(post_save, sender=Post)
def post_save_fire_queued_broadcasts(sender, instance: Post, created: bool, **kwargs):
    """When a Post transitions to published, fire any queued broadcasts.

    The drawer creates BroadcastJob rows with status=queued_on_publish
    while the post is still a draft. As soon as the user hits Publish,
    these rows flip to pending and run through the same _worker_run
    pipeline as immediate broadcasts.
    """
    from madga.webhooks import fire_event

    prev = getattr(instance, "_madga_prev_status", None)
    became_published = (
        instance.status == Post.STATUS_PUBLISHED and prev != Post.STATUS_PUBLISHED
    )
    became_unpublished = (
        prev == Post.STATUS_PUBLISHED and instance.status != Post.STATUS_PUBLISHED
    )

    # Webhook events ------------------------------------------------------
    payload = {
        "id": str(instance.id),
        "site_id": str(instance.site_id),
        "title": instance.title,
        "slug": instance.slug,
        "status": instance.status,
        "url": f"/blog/{instance.slug}/" if instance.slug else "",
    }
    if created:
        fire_event(instance.site, "post.updated", payload)
    if became_published:
        fire_event(instance.site, "post.published", payload)
    elif became_unpublished:
        fire_event(instance.site, "post.unpublished", payload)
    elif not created:
        fire_event(instance.site, "post.updated", payload)

    # Auto-broadcast on publish ------------------------------------------
    if not became_published:
        return
    from madga.models import BroadcastJob
    from madga.studio.views.broadcasts import _worker_run

    queued = BroadcastJob.objects.filter(
        related_post=instance,
        status=BroadcastJob.STATUS_QUEUED_ON_PUBLISH,
    )
    for job in queued:
        job.status = BroadcastJob.STATUS_PENDING
        job.save(update_fields=["status"])
        try:
            _worker_run(job)
        except Exception:  # noqa: BLE001 — never block the publish itself
            pass


@receiver(post_save, sender=Page)
def page_save_webhook(sender, instance: Page, created: bool, **kwargs):
    """Fire page.* webhook events on save."""
    from madga.webhooks import fire_event

    payload = {
        "id": str(instance.id),
        "site_id": str(instance.site_id),
        "title": instance.title,
        "slug": instance.slug,
        "url": f"/p/{instance.slug}/" if instance.slug else "",
    }
    if created:
        fire_event(instance.site, "page.updated", payload)
    elif instance.status == "published":
        fire_event(instance.site, "page.published", payload)
    else:
        fire_event(instance.site, "page.updated", payload)


@receiver(post_save, sender=MediaFile)
def mediafile_optimize_image(sender, instance: MediaFile, created: bool, **kwargs):
    """Generate responsive WebP variants when a new image is uploaded.

    Only runs on creation (so updating alt_text doesn't re-encode) and
    only for ``file_type == "image"`` rows that don't yet have variants.
    The optimizer itself is best-effort: a failure leaves the row
    untouched and ``MediaFile.srcset`` falls back to the original.
    """
    if not created:
        return
    if instance.file_type != "image":
        return
    if instance.variants:  # already optimized (e.g., test fixture)
        return
    try:
        from madga.imageopt import optimize
        optimize(instance)
    except Exception:  # noqa: BLE001 — never block a successful upload
        pass


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


@receiver(post_save, sender=MediaFile)
def mediafile_webhook(sender, instance: MediaFile, created: bool, **kwargs):
    if not created:
        return
    from madga.webhooks import fire_event
    fire_event(instance.site, "media.uploaded", {
        "id": str(instance.id),
        "site_id": str(instance.site_id),
        "filename": instance.filename,
        "file_type": instance.file_type,
        "url": instance.file.url if instance.file else "",
    })


if user_signed_up is not None:
    user_signed_up.connect(_on_allauth_user_signed_up)
