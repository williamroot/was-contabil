"""URLs da app TPV — Transação de Pequeno Valor."""

from django.urls import path

from apps.tpv.views import (
    HistoricoTPVView,
    ImportarCDAsView,
    SimularTPVView,
    WizardElegibilidadeView,
)

app_name = "tpv"

urlpatterns = [
    path("simular/", SimularTPVView.as_view(), name="simular"),
    path("wizard/", WizardElegibilidadeView.as_view(), name="wizard"),
    path("importar/", ImportarCDAsView.as_view(), name="importar"),
    path("historico/", HistoricoTPVView.as_view(), name="historico"),
]
