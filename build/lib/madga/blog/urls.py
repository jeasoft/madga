"""URL routes for the MADGA public blog."""

from django.urls import path

from .views import PostDetailView, PostListView

app_name = "madga_blog"

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),
    path("<slug:slug>/", PostDetailView.as_view(), name="post_detail"),
]
