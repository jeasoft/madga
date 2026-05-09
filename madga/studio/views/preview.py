"""Studio preview shell: renders the public-site URL of a post or page
inside an iframe with a device-size switcher (desktop / tablet / mobile)
and a "back to editor" toolbar — modeled after the prototype mockup.
"""

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from madga.models import Page, Post

from ..mixins import MadgaStudioMixin


DEVICE_SIZES = {
    "desktop": {"label": "Desktop", "width": 1280, "height": 800},
    "tablet": {"label": "Tablet", "width": 820, "height": 1180},
    "mobile": {"label": "Mobile", "width": 390, "height": 844},
}


class _BasePreviewView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/preview.html"
    object_kind = ""  # "post" or "page"
    public_url_prefix = ""  # "/blog/" or "/p/"
    edit_url_name = ""  # e.g. "madga_studio:post_edit"

    def _get_object(self, pk):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self._get_object(kwargs["pk"])
        device = self.request.GET.get("device", "desktop")
        if device not in DEVICE_SIZES:
            device = "desktop"
        ctx.update(
            obj=obj,
            object_kind=self.object_kind,
            public_url=f"{self.public_url_prefix}{obj.slug}/",
            edit_url_name=self.edit_url_name,
            device=device,
            device_sizes=DEVICE_SIZES,
            obj_title=obj.title or "Sin título",
        )
        return ctx


class PostPreviewView(_BasePreviewView):
    object_kind = "post"
    public_url_prefix = "/blog/"
    edit_url_name = "madga_studio:post_edit"

    def _get_object(self, pk):
        return get_object_or_404(
            Post.objects.alive().filter(site=self.get_site()), pk=pk
        )


class PagePreviewView(_BasePreviewView):
    object_kind = "page"
    public_url_prefix = "/p/"
    edit_url_name = "madga_studio:page_edit"

    def _get_object(self, pk):
        # Page does not use SoftDeleteMixin, so no `.alive()` here.
        return get_object_or_404(
            Page.objects.filter(site=self.get_site()), pk=pk
        )
