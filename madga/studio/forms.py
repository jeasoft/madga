"""Forms for the MADGA Studio."""

from django import forms

from madga.models import Category, Page, Post, Site, Tag


class PostForm(forms.ModelForm):
    body = forms.CharField(widget=forms.HiddenInput(), required=False)
    tag_names = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Post
        fields = [
            "title",
            "slug",
            "excerpt",
            "body",
            "status",
            "published_at",
            "category",
            "featured_image",
            "meta_title",
            "meta_description",
            "og_image",
            "focus_keyword",
            "canonical_url",
        ]
        widgets = {
            "published_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def clean_body(self):
        import json

        raw = self.cleaned_data.get("body") or ""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid Editor.js JSON.")


class PageForm(forms.ModelForm):
    body = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Page
        fields = [
            "title",
            "slug",
            "body",
            "status",
            "layout",
            "parent",
            "sort_order",
            "meta_title",
            "meta_description",
        ]

    def clean_body(self):
        import json

        raw = self.cleaned_data.get("body") or ""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid Editor.js JSON.")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "color", "description"]


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = [
            "name",
            "domain",
            "description",
            "logo",
            "favicon",
            "accent_color",
            "heading_font",
            "body_font",
            "border_radius",
            "content_density",
            "color_scheme",
            "theme",
            "meta_title",
            "meta_description",
            "timezone",
        ]
