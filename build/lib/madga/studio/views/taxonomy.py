"""Studio Categories + Tags management."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from slugify import slugify

from madga.models import Category, Tag

from ..forms import CategoryForm, TagForm
from ..mixins import MadgaStudioMixin


class TaxonomyListView(MadgaStudioMixin, TemplateView):
    template_name = "madga/studio/taxonomy.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = self.get_site()
        ctx["categories"] = Category.objects.filter(site=site) if site else []
        ctx["tags"] = Tag.objects.filter(site=site) if site else []
        ctx["category_form"] = CategoryForm()
        ctx["tag_form"] = TagForm()
        return ctx


class CategoryCreateView(MadgaStudioMixin, View):
    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site = self.get_site()
            if not obj.slug:
                obj.slug = slugify(obj.name)[:99]
            obj.save()
            messages.success(request, "Categoría creada.")
        else:
            messages.error(request, "No se pudo crear la categoría.")
        return redirect("madga_studio:taxonomy_list")


class CategoryDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(
            Category.objects.filter(site=self.get_site()), pk=pk
        )
        obj.delete()
        messages.success(request, "Categoría eliminada.")
        return redirect("madga_studio:taxonomy_list")


class TagCreateView(MadgaStudioMixin, View):
    def post(self, request):
        form = TagForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site = self.get_site()
            if not obj.slug:
                obj.slug = slugify(obj.name)[:99]
            obj.save()
            messages.success(request, "Tag creado.")
        else:
            messages.error(request, "No se pudo crear el tag.")
        return redirect("madga_studio:taxonomy_list")


class TagDeleteView(MadgaStudioMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(Tag.objects.filter(site=self.get_site()), pk=pk)
        obj.delete()
        messages.success(request, "Tag eliminado.")
        return redirect("madga_studio:taxonomy_list")
