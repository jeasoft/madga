"""URL routes for the MADGA Studio backoffice."""

from django.urls import path
from django.views.generic import RedirectView

from .views.auth import StudioLoginView, StudioLogoutView
from .views.dashboard import DashboardView
from .views.homepage import HomepageBuilderView
from .views.media import (
    MediaDeleteView,
    MediaListView,
    MediaPickerView,
    MediaUploadView,
)
from .views.navigation import NavigationView
from .views.pages import PageDeleteView, PageEditView, PageListView
from .views.posts import (
    PostBulkActionView,
    PostDeleteView,
    PostEditView,
    PostListView,
)
from .views.preview import (
    PagePreviewIframeView,
    PagePreviewView,
    PostPreviewIframeView,
    PostPreviewView,
)
from .views.settings import LayoutsView, SettingsView, ThemeView
from .views.themes import ThemeGalleryView
from .views.taxonomy import (
    CategoryCreateView,
    CategoryDeleteView,
    TagCreateView,
    TagDeleteView,
    TaxonomyListView,
)
from .views.api_keys import UserApiKeyListView
from .views.broadcasts import (
    BroadcastCancelView,
    BroadcastCreateView,
    BroadcastListView,
    BroadcastRetryView,
    SubscriberAddView,
    SubscriberDeleteView,
    SubscriberListView,
)
from .views.users import (
    AcceptInviteView,
    UserInviteView,
    UserListView,
    UserRoleUpdateView,
)
from .views.workspaces import WorkspaceCreateView, WorkspaceSwitchView

app_name = "madga_studio"

urlpatterns = [
    path("", RedirectView.as_view(url="/studio/dashboard/", permanent=False)),
    path("login/", StudioLoginView.as_view(), name="login"),
    path("logout/", StudioLogoutView.as_view(), name="logout"),

    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    path("posts/", PostListView.as_view(), name="post_list"),
    path("posts/new/", PostEditView.as_view(), name="post_create"),
    path("posts/<uuid:pk>/edit/", PostEditView.as_view(), name="post_edit"),
    path("posts/<uuid:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    path("posts/<uuid:pk>/preview/", PostPreviewView.as_view(), name="post_preview"),
    path("posts/<uuid:pk>/preview/iframe/", PostPreviewIframeView.as_view(), name="post_preview_iframe"),
    path("posts/bulk/", PostBulkActionView.as_view(), name="post_bulk"),

    path("pages/", PageListView.as_view(), name="page_list"),
    path("pages/new/", PageEditView.as_view(), name="page_create"),
    path("pages/<uuid:pk>/edit/", PageEditView.as_view(), name="page_edit"),
    path("pages/<uuid:pk>/delete/", PageDeleteView.as_view(), name="page_delete"),
    path("pages/<uuid:pk>/preview/", PagePreviewView.as_view(), name="page_preview"),
    path("pages/<uuid:pk>/preview/iframe/", PagePreviewIframeView.as_view(), name="page_preview_iframe"),

    path("media/", MediaListView.as_view(), name="media_list"),
    path("media/picker/", MediaPickerView.as_view(), name="media_picker"),
    path("media/upload/", MediaUploadView.as_view(), name="media_upload"),
    path("media/<uuid:pk>/delete/", MediaDeleteView.as_view(), name="media_delete"),

    path("taxonomy/", TaxonomyListView.as_view(), name="taxonomy_list"),
    path("taxonomy/categories/new/", CategoryCreateView.as_view(), name="category_create"),
    path("taxonomy/categories/<int:pk>/delete/", CategoryDeleteView.as_view(), name="category_delete"),
    path("taxonomy/tags/new/", TagCreateView.as_view(), name="tag_create"),
    path("taxonomy/tags/<int:pk>/delete/", TagDeleteView.as_view(), name="tag_delete"),

    path("users/", UserListView.as_view(), name="user_list"),
    path("users/invite/", UserInviteView.as_view(), name="user_invite"),
    path("users/<int:pk>/role/", UserRoleUpdateView.as_view(), name="user_role"),
    path("accept-invite/<str:token>/", AcceptInviteView.as_view(), name="accept_invite"),
    path("api-keys/", UserApiKeyListView.as_view(), name="api_keys"),

    path("settings/", SettingsView.as_view(), name="settings"),
    path("theme/", ThemeView.as_view(), name="theme"),
    path("theme-gallery/", ThemeGalleryView.as_view(), name="theme_gallery"),
    path("layouts/", LayoutsView.as_view(), name="layouts"),
    path("nav/", NavigationView.as_view(), name="navigation"),
    path("homepage/", HomepageBuilderView.as_view(), name="homepage_builder"),

    path("broadcasts/", BroadcastListView.as_view(), name="broadcast_list"),
    path("broadcasts/new/", BroadcastCreateView.as_view(), name="broadcast_create"),
    path("broadcasts/<uuid:pk>/retry/", BroadcastRetryView.as_view(), name="broadcast_retry"),
    path("broadcasts/<uuid:pk>/cancel/", BroadcastCancelView.as_view(), name="broadcast_cancel"),
    path("subscribers/", SubscriberListView.as_view(), name="subscriber_list"),
    path("subscribers/add/", SubscriberAddView.as_view(), name="subscriber_add"),
    path("subscribers/<uuid:pk>/delete/", SubscriberDeleteView.as_view(), name="subscriber_delete"),

    path("workspaces/new/", WorkspaceCreateView.as_view(), name="workspace_create"),
    path("workspaces/switch/", WorkspaceSwitchView.as_view(), name="workspace_switch"),
]
