"""Views de template (HTMX) para simulação de transação tributária.

Views de página que renderizam templates HTML.
Separadas das views DRF (API REST) em views.py.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView, TemplateView

from apps.transacao.models import Simulacao


class SimulacaoBasicaPageView(LoginRequiredMixin, TemplateView):
    """Página do formulário de simulação básica (Diagnóstico Prévio)."""

    template_name = "transacao/simulacao_basica.html"


class SimulacaoAvancadaPageView(LoginRequiredMixin, TemplateView):
    """Página do formulário de simulação avançada (CAPAG)."""

    template_name = "transacao/simulacao_avancada.html"


class HistoricoPageView(LoginRequiredMixin, ListView):
    """Página de histórico de simulações com busca e paginação."""

    template_name = "transacao/historico.html"
    context_object_name = "simulacoes"
    paginate_by = 20

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        qs = Simulacao.objects.all()
        if org is None:
            return qs.none()
        qs = qs.filter(organization=org).order_by("-created_at")

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(resultado__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class SimulacaoDetalhePageView(LoginRequiredMixin, DetailView):
    """Página de detalhe de uma simulação básica."""

    template_name = "transacao/resultado.html"
    context_object_name = "simulacao"

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        qs = Simulacao.objects.all()
        if org is None:
            return qs.none()
        return qs.filter(organization=org)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context["resultado"] = obj.resultado
        context["calculo_detalhes"] = obj.calculo_detalhes
        context["simulacao_id"] = str(obj.id)
        return context
