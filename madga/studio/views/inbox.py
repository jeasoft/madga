"""Studio inbox for FormSubmission rows."""

import csv

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, View

from madga.models import FormSubmission

from ..mixins import MadgaStudioMixin


class InboxListView(MadgaStudioMixin, ListView):
    template_name = "madga/studio/inbox.html"
    paginate_by = 30
    context_object_name = "submissions"

    def get_queryset(self):
        site = self.get_site()
        if site is None:
            return FormSubmission.objects.none()
        qs = FormSubmission.objects.filter(site=site)
        form_key = self.request.GET.get("form_key", "")
        if form_key:
            qs = qs.filter(form_key=form_key)
        unread_only = self.request.GET.get("unread") == "1"
        if unread_only:
            qs = qs.filter(is_read=False)
        q = self.request.GET.get("q", "").strip()
        if q:
            # JSON contains works on postgres + sqlite (text search on the JSON repr)
            qs = qs.filter(data__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        ctx["unread_count"] = (
            FormSubmission.objects.filter(site=site, is_read=False).count()
            if site else 0
        )
        ctx["form_keys"] = (
            FormSubmission.objects.filter(site=site)
            .values_list("form_key", flat=True).distinct()
            if site else []
        )
        ctx["current_form_key"] = self.request.GET.get("form_key", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["unread_only"] = self.request.GET.get("unread") == "1"
        return ctx


class InboxMarkReadView(MadgaStudioMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(FormSubmission, pk=pk, site=self.get_site())
        sub.is_read = not sub.is_read
        sub.save(update_fields=["is_read"])
        return HttpResponseRedirect(reverse("madga_studio:inbox_list"))


class InboxDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(FormSubmission, pk=pk, site=self.get_site())
        sub.delete()
        messages.success(request, _("Submission deleted."))
        return HttpResponseRedirect(reverse("madga_studio:inbox_list"))


class InboxExportView(MadgaStudioMixin, View):
    """CSV export of submissions for the current Site (filtered same as list)."""

    def get(self, request):
        site = self.get_site()
        if site is None:
            return HttpResponseRedirect(reverse("madga_studio:inbox_list"))
        qs = FormSubmission.objects.filter(site=site).order_by("-created_at")
        form_key = request.GET.get("form_key", "")
        if form_key:
            qs = qs.filter(form_key=form_key)

        # Collect every data key across rows so we get a stable column set.
        all_keys: list[str] = []
        seen = set()
        rows: list[dict] = []
        for s in qs.iterator():
            d = dict(s.data or {})
            for k in d.keys():
                if k not in seen:
                    seen.add(k)
                    all_keys.append(k)
            rows.append({
                "id": str(s.id),
                "form_key": s.form_key,
                "created_at": s.created_at.isoformat(),
                "source_url": s.source_url,
                "ip": s.ip or "",
                **d,
            })

        response = HttpResponse(content_type="text/csv")
        filename = f"madga-{site.domain}-{form_key or 'all'}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.DictWriter(
            response,
            fieldnames=["id", "form_key", "created_at", "source_url", "ip"] + all_keys,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return response
