"""Views de template (HTMX) para simulação TPV.

Views de página que renderizam templates HTML.
Separadas das views DRF (API REST) em views.py.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.tpv.models import SimulacaoTPV


class SimuladorCdaPageView(LoginRequiredMixin, TemplateView):
    """Página do simulador TPV por CDA."""

    template_name = "tpv/simulador_cda.html"


class WizardPageView(LoginRequiredMixin, TemplateView):
    """Página do wizard de elegibilidade TPV."""

    template_name = "tpv/wizard.html"


class ElegibilidadePageView(LoginRequiredMixin, TemplateView):
    """Dashboard de elegibilidade futura."""

    template_name = "tpv/elegibilidade.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = getattr(self.request, "organization", None)
        if org:
            context["simulacoes"] = SimulacaoTPV.objects.filter(
                organization=org,
            ).order_by(
                "-created_at"
            )[:50]
        else:
            context["simulacoes"] = SimulacaoTPV.objects.none()
        return context


class ImportCdasPageView(LoginRequiredMixin, TemplateView):
    """Página/modal de importação de CDAs."""

    template_name = "tpv/import_cdas.html"
