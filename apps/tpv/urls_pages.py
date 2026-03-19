"""URLs de páginas (templates HTMX) da app TPV."""

from django.urls import path

from apps.tpv.views_pages import (
    ElegibilidadePageView,
    ImportCdasPageView,
    SimuladorCdaPageView,
    WizardPageView,
)

app_name = "tpv"

urlpatterns = [
    path(
        "simulador/",
        SimuladorCdaPageView.as_view(),
        name="page-simular",
    ),
    path(
        "wizard/",
        WizardPageView.as_view(),
        name="page-wizard",
    ),
    path(
        "elegibilidade/",
        ElegibilidadePageView.as_view(),
        name="page-elegibilidade",
    ),
    path(
        "importar/",
        ImportCdasPageView.as_view(),
        name="page-importar",
    ),
]
