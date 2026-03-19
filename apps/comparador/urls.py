"""URLs da app Comparador — comparação de modalidades CAPAG vs TPV."""

from django.urls import path

from apps.comparador.views import CompararView

app_name = "comparador"

urlpatterns = [
    path("comparar/", CompararView.as_view(), name="comparar"),
]
