"""URLs para download de PDFs.

Padrão: /pdf/<tipo>/<uuid>/
"""

from django.urls import path

from apps.pdf.views import DiagnosticoPDFView, SimulacaoAvancadaPDFView, TPVPDFView

app_name = "pdf"

urlpatterns = [
    path(
        "diagnostico/<uuid:uuid>/",
        DiagnosticoPDFView.as_view(),
        name="diagnostico_pdf",
    ),
    path(
        "simulacao-avancada/<uuid:uuid>/",
        SimulacaoAvancadaPDFView.as_view(),
        name="simulacao_avancada_pdf",
    ),
    path(
        "tpv/<uuid:uuid>/",
        TPVPDFView.as_view(),
        name="tpv_pdf",
    ),
]
