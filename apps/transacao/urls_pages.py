"""URLs de páginas (templates HTMX) da app Transação."""

from django.urls import path

from apps.transacao.views_pages import (
    HistoricoPageView,
    SimulacaoAvancadaPageView,
    SimulacaoBasicaPageView,
    SimulacaoDetalhePageView,
)

app_name = "transacao"

urlpatterns = [
    path(
        "simular/basico/",
        SimulacaoBasicaPageView.as_view(),
        name="page-simular-basico",
    ),
    path(
        "simular/avancado/",
        SimulacaoAvancadaPageView.as_view(),
        name="page-simular-avancado",
    ),
    path(
        "historico/",
        HistoricoPageView.as_view(),
        name="page-historico",
    ),
    path(
        "<uuid:pk>/",
        SimulacaoDetalhePageView.as_view(),
        name="page-simulacao-detalhe",
    ),
]
