"""Studio dashboard."""

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from madga.models import Post

from ..mixins import MadgaStudioMixin


class DashboardView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        if site is None:
            ctx.update(stats={}, recent_posts=[])
            return ctx
        qs = Post.objects.alive().filter(site=site)

        now = timezone.now()
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        published_last_7d = qs.filter(
            status=Post.STATUS_PUBLISHED, published_at__gte=last_7d
        ).count()
        created_last_30d = qs.filter(created_at__gte=last_30d).count()

        ctx["stats"] = {
            "total": qs.count(),
            "published": qs.filter(status=Post.STATUS_PUBLISHED).count(),
            "draft": qs.filter(status=Post.STATUS_DRAFT).count(),
            "scheduled": qs.filter(status=Post.STATUS_SCHEDULED).count(),
            "views_total": qs.aggregate(total=Sum("views"))["total"] or 0,
            "published_last_7d": published_last_7d,
            "created_last_30d": created_last_30d,
        }
        ctx["recent_posts"] = list(
            qs.select_related("author", "category").order_by("-updated_at")[:6]
        )
        return ctx
