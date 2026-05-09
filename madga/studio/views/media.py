"""Studio Media library + Editor.js upload endpoint."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from madga.models import MediaFile

from ..mixins import MadgaStudioMixin


class MediaListView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/media.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        qs = MediaFile.objects.filter(site=site) if site else MediaFile.objects.none()
        kind = self.request.GET.get("kind")
        if kind in {MediaFile.TYPE_IMAGE, MediaFile.TYPE_VIDEO, MediaFile.TYPE_DOCUMENT}:
            qs = qs.filter(file_type=kind)
        ctx["media"] = qs.order_by("-created_at")
        ctx["current_kind"] = kind or "all"
        return ctx


def _media_to_editor_payload(media: MediaFile) -> dict:
    return {
        "success": 1,
        "file": {
            "url": media.file.url if media.file else "",
            "id": str(media.id),
            "width": media.width,
            "height": media.height,
        },
    }


class MediaUploadView(MadgaStudioMixin, View):
    """Editor.js byFile endpoint."""

    def post(self, request):
        site = self.get_site()
        if site is None:
            return JsonResponse({"success": 0, "error": "No site"}, status=400)
        upload = request.FILES.get("image") or request.FILES.get("file")
        if not upload:
            return JsonResponse({"success": 0, "error": "No file"}, status=400)

        ftype = MediaFile.TYPE_IMAGE
        ct = upload.content_type or ""
        if ct.startswith("video/"):
            ftype = MediaFile.TYPE_VIDEO
        elif not ct.startswith("image/"):
            ftype = MediaFile.TYPE_DOCUMENT

        media = MediaFile.objects.create(
            site=site,
            file=upload,
            filename=upload.name,
            mime_type=ct,
            size=upload.size,
            file_type=ftype,
            uploaded_by=request.user,
        )

        if ftype == MediaFile.TYPE_IMAGE:
            try:
                from PIL import Image

                with Image.open(media.file) as img:
                    media.width, media.height = img.width, img.height
                    media.save(update_fields=["width", "height"])
            except Exception:
                pass

        return JsonResponse(_media_to_editor_payload(media))


class MediaDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        media = get_object_or_404(MediaFile.objects.filter(site=self.get_site()), pk=pk)
        media.file.delete(save=False)
        media.delete()
        messages.success(request, "Archivo eliminado.")
        return redirect("madga_studio:media_list")
