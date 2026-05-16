"""Studio Posts CRUD."""

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from madga.models import Category, Post, Tag

from ..forms import PostForm
from ..mixins import MadgaStudioMixin


TAB_FILTERS = {
    "all": None,
    "published": "published",
    "draft": "draft",
    "scheduled": "scheduled",
    "trash": "archived",
}


class PostListView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/post_list.html"

    def _queryset(self):
        site = self.get_site()
        if site is None:
            return Post.objects.none()
        qs = Post.objects.alive().filter(site=site).select_related(
            "category", "author", "featured_image"
        )
        tab = self.request.GET.get("tab", "all")
        wanted = TAB_FILTERS.get(tab)
        if tab == "trash":
            return Post.objects.deleted().filter(site=site)
        if wanted:
            qs = qs.filter(status=wanted)
        else:
            qs = qs.exclude(status=Post.STATUS_ARCHIVED)
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(slug__icontains=search))
        return qs.order_by("-updated_at")

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["madga/studio/components/post_list_rows.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        all_qs = Post.objects.alive().filter(site=site) if site else Post.objects.none()
        counts = {
            "all": all_qs.exclude(status=Post.STATUS_ARCHIVED).count() if site else 0,
            "published": all_qs.filter(status=Post.STATUS_PUBLISHED).count() if site else 0,
            "draft": all_qs.filter(status=Post.STATUS_DRAFT).count() if site else 0,
            "scheduled": all_qs.filter(status=Post.STATUS_SCHEDULED).count() if site else 0,
            "trash": Post.objects.deleted().filter(site=site).count() if site else 0,
        }
        # Paginate (20 per page).
        paginator = Paginator(self._queryset(), 20)
        try:
            page = paginator.page(int(self.request.GET.get("page") or 1))
        except (ValueError, EmptyPage):
            page = paginator.page(1)
        ctx.update(
            posts=page.object_list,
            page_obj=page,
            paginator=paginator,
            current_tab=self.request.GET.get("tab", "all"),
            search_q=self.request.GET.get("q", ""),
            counts=counts,
            posts_count=counts["all"],
            tabs=[
                {"key": "all",       "label": "Todos",       "count": counts["all"]},
                {"key": "published", "label": "Publicados",  "count": counts["published"]},
                {"key": "draft",     "label": "Borradores",  "count": counts["draft"]},
                {"key": "scheduled", "label": "Programados", "count": counts["scheduled"]},
                {"key": "trash",     "label": "Papelera",    "count": counts["trash"]},
            ],
        )
        return ctx


class PostBulkActionView(MadgaStudioMixin, View):
    def post(self, request):
        site = self.get_site()
        action = request.POST.get("action")
        ids = request.POST.getlist("ids")
        qs = Post.objects.filter(site=site, id__in=ids)

        # Per-action permission checks.
        if action == "publish" and not self.has_perm("publish_post"):
            messages.error(request, _("Tu rol no permite publicar."))
            return redirect(request.META.get("HTTP_REFERER", "/studio/posts/"))
        if action in ("trash", "delete"):
            # Filter to posts the user can actually delete.
            allowed_ids = [str(p.pk) for p in qs if self.can_delete_post(p)]
            if len(allowed_ids) != len(ids):
                messages.warning(
                    request,
                    f"Algunos posts no fueron procesados por permisos ({len(ids) - len(allowed_ids)} omitidos).",
                )
            qs = qs.filter(pk__in=allowed_ids)

        if action == "publish":
            qs.update(status=Post.STATUS_PUBLISHED, published_at=timezone.now())
        elif action == "draft":
            qs.update(status=Post.STATUS_DRAFT)
        elif action == "trash":
            for p in qs:
                p.soft_delete()
        elif action == "restore":
            qs.update(is_deleted=False, deleted_at=None)
        elif action == "delete":
            qs.delete()
        return redirect(request.META.get("HTTP_REFERER", "/studio/posts/"))


class PostEditView(MadgaStudioMixin, View):
    template_name = "madga/studio/post_edit.html"

    def _get_post(self, pk):
        if not pk:
            return None
        return get_object_or_404(
            Post.objects.alive().filter(site=self.get_site()), pk=pk
        )

    def get(self, request, pk=None):
        from madga.publishers import all_publishers

        post = self._get_post(pk)
        site = self.get_site()
        if post is not None and not self.can_edit_post(post):
            raise PermissionDenied(_("You can't edit this post."))
        form = PostForm(instance=post)
        return render(
            request,
            self.template_name,
            {
                "post": post,
                "form": form,
                "categories": Category.objects.filter(site=site),
                "tags": Tag.objects.filter(site=site),
                "site": site,
                "membership": self.get_membership(),
                "post_body_json": json.dumps(post.body if post else {}),
                "selected_tag_slugs": list(post.tags.values_list("slug", flat=True)) if post else [],
                "broadcast_publishers": all_publishers(only_configured=True, site=site),
            },
        )

    def post(self, request, pk=None):
        post = self._get_post(pk)
        # Edits to existing posts must pass the per-post check.
        if post is not None and not self.can_edit_post(post):
            raise PermissionDenied(_("You can't edit this post."))
        # Creating new posts requires SOME role (Contributor minimum).
        if post is None and self.get_membership() is None and not request.user.is_superuser:
            raise PermissionDenied(_("No membership in this site."))
        # Publishing requires publish_post; downgrade to draft if not allowed.
        if post is None or post.status != Post.STATUS_PUBLISHED:
            if request.POST.get("status") == Post.STATUS_PUBLISHED and not self.has_perm("publish_post"):
                # Silent downgrade so a Contributor can still save as draft.
                post_data = request.POST.copy()
                post_data["status"] = Post.STATUS_DRAFT
                request.POST = post_data
                messages.warning(request, _("Tu rol no permite publicar — guardado como borrador."))
        form = PostForm(request.POST, request.FILES, instance=post)
        if not form.is_valid():
            if request.headers.get("HX-Request") or request.headers.get(
                "X-Requested-With"
            ) == "XMLHttpRequest":
                return JsonResponse({"ok": False, "errors": form.errors}, status=400)
            return render(
                request,
                self.template_name,
                {
                    "post": post,
                    "form": form,
                    "categories": Category.objects.filter(site=self.get_site()),
                    "tags": Tag.objects.filter(site=self.get_site()),
                    "site": self.get_site(),
                    "membership": self.get_membership(),
                    "post_body_json": form.data.get("body", "{}"),
                    "selected_tag_slugs": request.POST.getlist("tag_slugs"),
                },
            )
        instance = form.save(commit=False)
        instance.site = self.get_site()
        if not instance.author_id:
            instance.author = request.user
        if instance.status == Post.STATUS_PUBLISHED and not instance.published_at:
            instance.published_at = timezone.now()
        instance.save()

        # tags
        tag_slugs = request.POST.getlist("tag_slugs")
        if tag_slugs:
            tags = Tag.objects.filter(site=self.get_site(), slug__in=tag_slugs)
            instance.tags.set(tags)
        else:
            instance.tags.clear()

        if request.headers.get("HX-Request") or request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest":
            return JsonResponse(
                {"ok": True, "id": str(instance.id), "slug": instance.slug}
            )
        messages.success(request, f"Post «{instance.title}» guardado.")
        return redirect("madga_studio:post_edit", pk=instance.pk)


class PostDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(
            Post.objects.alive().filter(site=self.get_site()), pk=pk
        )
        if not self.can_delete_post(post):
            raise PermissionDenied(_("You can't delete this post."))
        post.soft_delete()
        messages.success(request, _("Post enviado a la papelera."))
        return redirect("madga_studio:post_list")
