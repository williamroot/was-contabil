"""URLs da app Transação — simulação básica e avançada."""

from django.urls import path

from apps.transacao.views import (
    HistoricoView,
    SimulacaoDetalheView,
    SimularAvancadoView,
    SimularBasicoView,
)

app_name = "transacao"

urlpatterns = [
    path("simular/basico/", SimularBasicoView.as_view(), name="simular-basico"),
    path("simular/avancado/", SimularAvancadoView.as_view(), name="simular-avancado"),
    path("historico/", HistoricoView.as_view(), name="historico"),
    path("<uuid:pk>/", SimulacaoDetalheView.as_view(), name="simulacao-detalhe"),
]
