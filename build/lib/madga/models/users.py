"""SiteUser (roles) and UserInvitation."""

import secrets

from django.conf import settings
from django.db import models

from .base import TimestampMixin


class SiteUser(TimestampMixin, models.Model):
    ROLE_OWNER = "owner"
    ROLE_EDITOR = "editor"
    ROLE_AUTHOR = "author"
    ROLE_CONTRIBUTOR = "contributor"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_AUTHOR, "Author"),
        (ROLE_CONTRIBUTOR, "Contributor"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="madga_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_AUTHOR)

    class Meta:
        unique_together = [["site", "user"]]

    def __str__(self) -> str:
        return f"{self.user} @ {self.site} ({self.role})"


def _new_invite_token() -> str:
    return secrets.token_urlsafe(32)


class UserInvitation(TimestampMixin, models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_EXPIRED, "Expired"),
    ]

    site = models.ForeignKey(
        "madga.Site", on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20, choices=SiteUser.ROLE_CHOICES, default=SiteUser.ROLE_AUTHOR
    )
    token = models.CharField(max_length=64, unique=True, default=_new_invite_token)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="madga_invites_sent",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["site", "email"]]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} → {self.site} ({self.role})"
