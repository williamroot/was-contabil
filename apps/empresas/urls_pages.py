"""URLs de paginas de empresas."""

from django.urls import path

from apps.empresas.views_pages import EmpresasPageView

app_name = "empresas-pages"

urlpatterns = [
    path("", EmpresasPageView.as_view(), name="list"),
]
