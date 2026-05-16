"""Studio Pages CRUD."""

import json

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from madga.models import Page

from ..forms import PageForm
from ..mixins import MadgaStudioMixin


class PageListView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/page_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        ctx["pages"] = (
            Page.objects.filter(site=site).order_by("sort_order", "title")
            if site
            else []
        )
        return ctx


class PageEditView(MadgaStudioMixin, View):
    template_name = "madga/studio/page_edit.html"

    def _get_page(self, pk):
        if not pk:
            return None
        return get_object_or_404(Page.objects.filter(site=self.get_site()), pk=pk)

    def get(self, request, pk=None):
        page = self._get_page(pk)
        return render(
            request,
            self.template_name,
            {
                "page_obj": page,
                "form": PageForm(instance=page),
                "page_body_json": json.dumps(page.body if page else {}),
                "site": self.get_site(),
                "membership": self.get_membership(),
            },
        )

    def post(self, request, pk=None):
        page = self._get_page(pk)
        form = PageForm(request.POST, instance=page)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "page_obj": page,
                    "form": form,
                    "page_body_json": form.data.get("body", "{}"),
                    "site": self.get_site(),
                    "membership": self.get_membership(),
                },
            )
        instance = form.save(commit=False)
        instance.site = self.get_site()
        instance.save()
        messages.success(request, _("Page «%(title)s» saved.") % {"title": instance.title})
        return redirect("madga_studio:page_edit", pk=instance.pk)


class PageDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        page = get_object_or_404(Page.objects.filter(site=self.get_site()), pk=pk)
        page.delete()
        messages.success(request, _("Página eliminada."))
        return redirect("madga_studio:page_list")
