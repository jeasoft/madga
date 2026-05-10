"""Studio preview: an iframe shell + content endpoints that render the
public template chain WITHOUT the publish filter, so drafts can be
previewed in their real visual form.
"""

from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView

from madga.blog.views import _themed_templates
from madga.models import Page, Post

from ..mixins import MadgaStudioMixin


DEVICE_SIZES = {
    "desktop": {"label": "Desktop", "width": 1280, "height": 800},
    "tablet": {"label": "Tablet", "width": 820, "height": 1180},
    "mobile": {"label": "Mobile", "width": 390, "height": 844},
}


class _BasePreviewView(MadgaStudioMixin, TemplateView):
    """Iframe shell. The iframe loads a content endpoint (one per kind) that
    bypasses the publish filter, so drafts render fully. The "Abrir" link
    still points at the public URL — that one only resolves for published
    content, and is hidden via {% if is_published %} in the template."""

    template_name = "madga/studio/preview.html"
    object_kind = ""  # "post" or "page"
    public_url_prefix = ""  # "/blog/" or "/p/"
    iframe_url_name = ""
    edit_url_name = ""

    def _get_object(self, pk):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        from django.urls import reverse

        ctx = super().get_context_data(**kwargs)
        obj = self._get_object(kwargs["pk"])
        device = self.request.GET.get("device", "desktop")
        if device not in DEVICE_SIZES:
            device = "desktop"
        ctx.update(
            obj=obj,
            object_kind=self.object_kind,
            public_url=f"{self.public_url_prefix}{obj.slug}/",
            iframe_url=reverse(self.iframe_url_name, kwargs={"pk": obj.pk}),
            is_published=getattr(obj, "status", "") == "published",
            edit_url_name=self.edit_url_name,
            device=device,
            device_sizes=DEVICE_SIZES,
            obj_title=obj.title or "Sin título",
        )
        return ctx


class PostPreviewView(_BasePreviewView):
    object_kind = "post"
    public_url_prefix = "/blog/"
    iframe_url_name = "madga_studio:post_preview_iframe"
    edit_url_name = "madga_studio:post_edit"

    def _get_object(self, pk):
        return get_object_or_404(
            Post.objects.alive().filter(site=self.get_site()), pk=pk
        )


class PagePreviewView(_BasePreviewView):
    object_kind = "page"
    public_url_prefix = "/p/"
    iframe_url_name = "madga_studio:page_preview_iframe"
    edit_url_name = "madga_studio:page_edit"

    def _get_object(self, pk):
        return get_object_or_404(Page.objects.filter(site=self.get_site()), pk=pk)


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PostPreviewIframeView(MadgaStudioMixin, View):
    """Renders a post's content using the public template chain regardless of
    publish status. xframe_options_sameorigin lets the studio's iframe load it.
    """

    def get(self, request, pk):
        site = self.get_site()
        post = get_object_or_404(Post.objects.alive().filter(site=site), pk=pk)
        return render(
            request,
            _themed_templates(site, "detail"),
            {"site": site, "post": post, "is_studio_preview": True},
        )


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PagePreviewIframeView(MadgaStudioMixin, View):
    def get(self, request, pk):
        site = self.get_site()
        page = get_object_or_404(Page.objects.filter(site=site), pk=pk)
        layout = page.layout or "simple"
        theme = (site.theme if site else "default") or "default"
        return render(
            request,
            [
                f"madga/themes/{theme}/page-{layout}.html",
                f"madga/themes/{theme}/page.html",
                f"madga/blog/page-{layout}.html",
                "madga/blog/page.html",
            ],
            {"site": site, "page": page, "is_studio_preview": True},
        )
