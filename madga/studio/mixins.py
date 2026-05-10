"""Mixins for Studio views."""

from django.contrib.auth.mixins import LoginRequiredMixin

from madga.models import Site, SiteUser


ROLE_PERMISSIONS = {
    SiteUser.ROLE_OWNER: {
        "publish_post", "edit_any_post", "delete_post",
        "manage_media", "manage_users", "manage_settings", "manage_pages",
    },
    SiteUser.ROLE_EDITOR: {
        "publish_post", "edit_any_post", "delete_post",
        "manage_media", "manage_pages",
    },
    SiteUser.ROLE_AUTHOR: {
        "publish_post", "manage_media", "delete_own_post",
    },
    SiteUser.ROLE_CONTRIBUTOR: {"manage_media"},
}


class MadgaStudioMixin(LoginRequiredMixin):
    """Adds get_site() and get_membership() helpers, plus login-required."""

    login_url = "/studio/login/"

    def get_site(self) -> Site | None:
        return getattr(self.request, "madga_site", None)

    def get_membership(self) -> SiteUser | None:
        return getattr(self.request, "madga_membership", None)

    def has_perm(self, perm: str) -> bool:
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        if membership is None:
            return False
        return perm in ROLE_PERMISSIONS.get(membership.role, set())

    def can_edit_post(self, post) -> bool:
        """A user can edit a post if they own the post OR have edit_any_post."""
        if self.request.user.is_superuser:
            return True
        if self.has_perm("edit_any_post"):
            return True
        # Authors/Contributors with their own post
        return post.author_id == self.request.user.id

    def can_delete_post(self, post) -> bool:
        """delete_post (Owner/Editor) or delete_own_post (Author on own post)."""
        if self.request.user.is_superuser:
            return True
        if self.has_perm("delete_post"):
            return True
        return self.has_perm("delete_own_post") and post.author_id == self.request.user.id

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs) if hasattr(super(), "get_context_data") else {}
        ctx.update(
            site=self.get_site(),
            membership=self.get_membership(),
        )
        return ctx
