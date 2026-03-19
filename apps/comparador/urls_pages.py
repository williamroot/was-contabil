"""URLs de paginas do comparador."""

from django.urls import path

from apps.comparador.views import ComparadorPageView

app_name = "comparador-pages"

urlpatterns = [
    path("", ComparadorPageView.as_view(), name="comparacao"),
]
