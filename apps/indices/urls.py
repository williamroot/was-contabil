"""URLs da app Indices — índices econômicos SELIC."""

from django.urls import path

from apps.indices.views import SelicAcumuladaView, SelicUltimosView

app_name = "indices"

urlpatterns = [
    path("selic/ultimos/", SelicUltimosView.as_view(), name="selic-ultimos"),
    path("selic/acumulada/", SelicAcumuladaView.as_view(), name="selic-acumulada"),
]
