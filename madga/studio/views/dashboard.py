"""Studio dashboard."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView

from madga.models import Post

from ..mixins import MadgaStudioMixin


def _series_last_n_days(qs, n: int, date_field: str):
    """Return a list of ints, length n, oldest→newest, counting rows of qs
    with date_field falling on each day in [today-n+1, today]."""
    now = timezone.now()
    start = (now - timedelta(days=n - 1)).date()
    by_day = (
        qs.filter(**{f"{date_field}__date__gte": start})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(c=Count("id"))
    )
    counts = {row["day"]: row["c"] for row in by_day}
    return [counts.get(start + timedelta(days=i), 0) for i in range(n)]


def _spark_path(values, w: int = 90, h: int = 28) -> str:
    """Build an SVG polyline `d` attribute from a value series."""
    if not values:
        return ""
    vmax = max(values) or 1
    n = len(values)
    if n == 1:
        return f"M0,{h//2} L{w},{h//2}"
    step = w / (n - 1)
    pts = []
    for i, v in enumerate(values):
        x = i * step
        y = h - (v / vmax) * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    return "M" + " L".join(pts)


def _greeting(now) -> str:
    h = now.hour
    if h < 6:
        return "Buenas noches"
    if h < 13:
        return "Buenos días"
    if h < 19:
        return "Buenas tardes"
    return "Buenas noches"


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
        prev_30d = now - timedelta(days=60)

        published_last_7d = qs.filter(
            status=Post.STATUS_PUBLISHED, published_at__gte=last_7d
        ).count()
        created_last_30d = qs.filter(created_at__gte=last_30d).count()

        # Views delta vs previous 30d window — proxy via published-in-window.
        views_now = qs.filter(updated_at__gte=last_30d).aggregate(
            total=Sum("views")
        )["total"] or 0
        views_prev = qs.filter(
            updated_at__gte=prev_30d, updated_at__lt=last_30d
        ).aggregate(total=Sum("views"))["total"] or 0
        if views_prev:
            views_delta_pct = round((views_now - views_prev) * 100.0 / views_prev, 1)
        else:
            views_delta_pct = None

        # Sparkline series (last 14 days).
        spark_total = _series_last_n_days(qs, 14, "created_at")
        spark_published = _series_last_n_days(
            qs.filter(status=Post.STATUS_PUBLISHED), 14, "published_at"
        )
        spark_drafts = _series_last_n_days(
            qs.filter(status=Post.STATUS_DRAFT), 14, "updated_at"
        )
        spark_views = spark_published  # proxy: a published post likely drove views.

        ctx["stats"] = {
            "total": qs.count(),
            "published": qs.filter(status=Post.STATUS_PUBLISHED).count(),
            "draft": qs.filter(status=Post.STATUS_DRAFT).count(),
            "scheduled": qs.filter(status=Post.STATUS_SCHEDULED).count(),
            "views_total": qs.aggregate(total=Sum("views"))["total"] or 0,
            "published_last_7d": published_last_7d,
            "created_last_30d": created_last_30d,
            "views_delta_pct": views_delta_pct,
            "spark_total": _spark_path(spark_total),
            "spark_published": _spark_path(spark_published),
            "spark_drafts": _spark_path(spark_drafts),
            "spark_views": _spark_path(spark_views),
        }
        ctx["greeting"] = _greeting(timezone.localtime(now))
        ctx["recent_posts"] = list(
            qs.select_related("author", "category").order_by("-updated_at")[:6]
        )
        return ctx
