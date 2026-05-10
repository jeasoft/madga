"""Lightweight Django admin registration for sanity checks."""

from django.contrib import admin

from madga.models import (
    Category,
    MediaFile,
    Page,
    Post,
    Site,
    SiteUser,
    Tag,
    UserInvitation,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "theme", "is_active")
    search_fields = ("name", "domain")
    readonly_fields = ("api_key",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "site", "author", "published_at", "views")
    list_filter = ("status", "site", "category")
    search_fields = ("title", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "author", "featured_image", "og_image")
    filter_horizontal = ("tags",)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "site", "layout")
    list_filter = ("status", "site")
    search_fields = ("title", "slug")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "site")
    list_filter = ("site",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "site")
    list_filter = ("site",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("filename", "file_type", "site", "size", "uploaded_by")
    list_filter = ("file_type", "site")
    search_fields = ("filename", "alt_text")


@admin.register(SiteUser)
class SiteUserAdmin(admin.ModelAdmin):
    list_display = ("user", "site", "role")
    list_filter = ("role", "site")


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "site", "role", "status", "created_at")
    list_filter = ("status", "site", "role")
    search_fields = ("email",)
