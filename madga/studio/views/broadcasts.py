"""Studio views for the broadcast feature."""

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, View

from madga.models import BroadcastJob, Post, Subscriber
from madga.publishers import all_publishers, get_publisher

from ..mixins import MadgaStudioMixin


def _worker_run(job):
    """Execute a job in the current process. Caller decides sync vs. thread."""
    job.mark_running()
    publisher = get_publisher(job.publisher_key)
    if publisher is None:
        job.error_log = [{"target": "<system>", "msg": f"Publisher '{job.publisher_key}' is not registered."}]
        job.failed_count = job.targets_count
        job.mark_finished()
        return
    try:
        result = publisher.publish(job)
    except Exception as e:  # noqa: BLE001
        job.error_log = (job.error_log or []) + [{"target": "<system>", "msg": str(e)}]
        job.failed_count = job.targets_count
        job.mark_finished()
        return
    job.sent_count = result.sent
    job.failed_count = result.failed
    job.error_log = (job.error_log or []) + list(result.errors)
    job.save(update_fields=["sent_count", "failed_count", "error_log"])
    job.mark_finished()


class BroadcastListView(MadgaStudioMixin, ListView):
    template_name = "madga/studio/broadcasts.html"
    paginate_by = 25
    context_object_name = "jobs"

    def get_queryset(self):
        return (
            BroadcastJob.objects.filter(site=self.get_site())
            .select_related("related_post", "related_page", "created_by")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["publishers"] = all_publishers(only_configured=True, site=self.get_site())
        site = self.get_site()
        ctx["subscriber_count"] = (
            Subscriber.objects.filter(site=site, is_active=True).count() if site else 0
        )
        return ctx


class BroadcastCreateView(MadgaStudioMixin, View):
    """Compose a new BroadcastJob and run it (synchronously for now).

    POST fields:
      - post_id          : optional UUID of a Post being broadcast
      - publisher_keys   : list of publisher keys to fan out to
      - subject          : override snapshot subject (otherwise derived from post)
      - body_html        : optional body override
      - scheduled_at     : optional ISO datetime; if set, queued for the worker
    """

    def post(self, request):
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))
        post_id = request.POST.get("post_id") or None
        post = None
        if post_id:
            post = get_object_or_404(Post, pk=post_id, site=site)

        publisher_keys = request.POST.getlist("publisher_keys")
        if not publisher_keys:
            messages.error(request, _("Pick at least one publisher."))
            return HttpResponseRedirect(self._redirect_target(post))

        subject = (request.POST.get("subject") or "").strip()
        if not subject and post:
            subject = post.title
        if not subject:
            messages.error(request, _("Subject is required."))
            return HttpResponseRedirect(self._redirect_target(post))

        body_html = request.POST.get("body_html") or (post.body_html if post else "")
        body_text = request.POST.get("body_text") or ""
        related_url = ""
        if post and post.slug:
            related_url = f"/blog/{post.slug}/"
            domain = (site.domain or "").strip()
            if domain and not domain.startswith("http"):
                scheme = "https" if domain != "localhost" else "http"
                related_url = f"{scheme}://{domain}{related_url}"

        scheduled = request.POST.get("scheduled_at") or None

        created = []
        for key in publisher_keys:
            publisher = get_publisher(key)
            if publisher is None:
                continue
            targets = publisher.estimate_targets(_FakeJobForEstimate(site=site))
            job = BroadcastJob.objects.create(
                site=site,
                publisher_key=key,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                related_url=related_url,
                related_post=post,
                targets_count=targets,
                scheduled_at=scheduled or None,
                created_by=request.user if request.user.is_authenticated else None,
            )
            created.append(job)

        # Sync run for every job that's not scheduled in the future. The
        # async worker (madga broadcast-worker) handles scheduled ones.
        from django.utils import timezone
        now = timezone.now()
        for job in created:
            if not job.scheduled_at or job.scheduled_at <= now:
                _worker_run(job)

        if len(created) == 1:
            messages.success(
                request,
                _("Broadcast queued (%(n)d recipient(s)).") % {"n": created[0].targets_count},
            )
        else:
            messages.success(
                request,
                _("%(n)d broadcasts queued.") % {"n": len(created)},
            )
        return HttpResponseRedirect(self._redirect_target(post))

    def _redirect_target(self, post):
        if post:
            return reverse("madga_studio:post_edit", kwargs={"pk": post.pk})
        return reverse("madga_studio:broadcast_list")


class BroadcastRetryView(MadgaStudioMixin, View):
    """Re-run a failed/partial broadcast: rebuild the targets and try again."""

    def post(self, request, pk):
        site = self.get_site()
        job = get_object_or_404(BroadcastJob, pk=pk, site=site)
        if job.status not in (BroadcastJob.STATUS_FAILED, BroadcastJob.STATUS_PARTIAL):
            messages.error(request, _("Only failed or partial broadcasts can be retried."))
            return HttpResponseRedirect(reverse("madga_studio:broadcast_list"))
        # Reset counters then re-run.
        job.sent_count = 0
        job.failed_count = 0
        job.error_log = []
        publisher = get_publisher(job.publisher_key)
        if publisher is not None:
            job.targets_count = publisher.estimate_targets(job)
        job.save(update_fields=["sent_count", "failed_count", "error_log", "targets_count"])
        _worker_run(job)
        messages.success(request, _("Broadcast retried."))
        return HttpResponseRedirect(reverse("madga_studio:broadcast_list"))


class BroadcastCancelView(MadgaStudioMixin, View):
    def post(self, request, pk):
        site = self.get_site()
        job = get_object_or_404(BroadcastJob, pk=pk, site=site)
        if job.status not in (BroadcastJob.STATUS_PENDING,):
            messages.error(request, _("Only pending broadcasts can be cancelled."))
            return HttpResponseRedirect(reverse("madga_studio:broadcast_list"))
        job.cancel()
        messages.success(request, _("Broadcast cancelled."))
        return HttpResponseRedirect(reverse("madga_studio:broadcast_list"))


class SubscriberListView(MadgaStudioMixin, ListView):
    template_name = "madga/studio/subscribers.html"
    paginate_by = 50
    context_object_name = "subscribers"

    def get_queryset(self):
        site = self.get_site()
        qs = Subscriber.objects.filter(site=site) if site else Subscriber.objects.none()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(email__icontains=q)
        kind = self.request.GET.get("kind", "active")
        if kind == "active":
            qs = qs.filter(is_active=True)
        elif kind == "unsubscribed":
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        ctx["active_count"] = Subscriber.objects.filter(site=site, is_active=True).count() if site else 0
        ctx["unsubscribed_count"] = Subscriber.objects.filter(site=site, is_active=False).count() if site else 0
        ctx["q"] = self.request.GET.get("q", "")
        ctx["current_kind"] = self.request.GET.get("kind", "active")
        return ctx


class SubscriberAddView(MadgaStudioMixin, View):
    def post(self, request):
        site = self.get_site()
        if site is None:
            return HttpResponseBadRequest(_("No active site."))
        email = (request.POST.get("email") or "").strip()
        if not email:
            messages.error(request, _("Email is required."))
            return HttpResponseRedirect(reverse("madga_studio:subscriber_list"))
        sub, created = Subscriber.objects.get_or_create(
            site=site, email=email,
            defaults={"source": Subscriber.SOURCE_MANUAL},
        )
        if not created and not sub.is_active:
            sub.is_active = True
            sub.unsubscribed_at = None
            sub.save(update_fields=["is_active", "unsubscribed_at"])
            messages.success(request, _("Subscriber re-activated."))
        elif created:
            messages.success(request, _("Subscriber added."))
        else:
            messages.info(request, _("Subscriber already exists."))
        return HttpResponseRedirect(reverse("madga_studio:subscriber_list"))


class SubscriberDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        site = self.get_site()
        sub = get_object_or_404(Subscriber, pk=pk, site=site)
        sub.delete()
        messages.success(request, _("Subscriber removed."))
        return HttpResponseRedirect(reverse("madga_studio:subscriber_list"))


class _FakeJobForEstimate:
    """Minimal stand-in so ``Publisher.estimate_targets`` can run before
    the BroadcastJob row exists (we call it during the POST handler to
    fill ``targets_count``)."""

    def __init__(self, site):
        self.site = site
