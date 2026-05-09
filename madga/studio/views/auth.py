"""Login/logout for the Studio."""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views import View


class StudioLoginView(View):
    template_name = "madga/studio/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(request.GET.get("next") or "/studio/")
        return render(
            request,
            self.template_name,
            {"form": AuthenticationForm(), "next": request.GET.get("next", "")},
        )

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.POST.get("next") or "/studio/")
        return render(
            request,
            self.template_name,
            {"form": form, "next": request.POST.get("next", "")},
        )


class StudioLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("/studio/login/")

    post = get
