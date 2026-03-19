from django.urls import path

from apps.core.views import (
    HomeView,
    InvitePageView,
    LoginPageView,
    OrganizationSetupPageView,
)

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("login/", LoginPageView.as_view(), name="login"),
    path(
        "convite/<str:token>/",
        InvitePageView.as_view(),
        name="invite",
    ),
    path(
        "organizacao/setup/",
        OrganizationSetupPageView.as_view(),
        name="organization-setup",
    ),
]
