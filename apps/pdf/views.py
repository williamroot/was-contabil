"""Views para download de PDFs gerados via WeasyPrint.

Cada view busca a simulacao do banco de dados pelo UUID,
monta o contexto a partir do campo resultado (JSONField)
e gera o PDF correspondente.

Seguranca: todas as views exigem autenticacao (LoginRequiredMixin)
e filtram por organization do request (multi-tenant).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.views import View

from apps.pdf.generators import gerar_pdf
from apps.tpv.models import SimulacaoTPV
from apps.transacao.models import Simulacao, SimulacaoAvancada


class DiagnosticoPDFView(LoginRequiredMixin, View):
    """Gera e retorna PDF do diagnostico previo de transacao tributaria.

    GET /pdf/diagnostico/<uuid>/ -> download PDF diagnostico.

    Busca Simulacao pelo UUID com filtro de organization (multi-tenant).
    """

    def get(self, request, uuid):
        """Gera PDF do diagnostico e retorna como download."""
        simulacao = Simulacao.objects.filter(organization=request.organization, id=uuid).first()
        if not simulacao:
            raise Http404("Simulacao nao encontrada.")

        context = {
            "razao_social": simulacao.razao_social,
            "cnpj": simulacao.cnpj,
            **(simulacao.resultado or {}),
        }
        pdf_bytes = gerar_pdf("diagnostico.html", context)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="diagnostico_{simulacao.cnpj or uuid}.pdf"'
        return response


class SimulacaoAvancadaPDFView(LoginRequiredMixin, View):
    """Gera e retorna PDF da simulacao avancada de transacao tributaria.

    GET /pdf/simulacao-avancada/<uuid>/?modo=resumido -> PDF resumido (padrao).
    GET /pdf/simulacao-avancada/<uuid>/?modo=completo -> PDF com fluxo completo.

    Busca SimulacaoAvancada pelo UUID com filtro de organization (multi-tenant).
    """

    def get(self, request, uuid):
        """Gera PDF da simulacao avancada e retorna como download."""
        simulacao = SimulacaoAvancada.objects.filter(organization=request.organization, id=uuid).first()
        if not simulacao:
            raise Http404("Simulacao nao encontrada.")

        modo = request.GET.get("modo", "resumido")
        if modo == "completo":
            template_name = "simulacao_avancada_completo.html"
        else:
            template_name = "simulacao_avancada_resumido.html"

        context = {**(simulacao.resultado or {})}
        pdf_bytes = gerar_pdf(template_name, context)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="simulacao_avancada_{modo}_{uuid}.pdf"'
        return response


class TPVPDFView(LoginRequiredMixin, View):
    """Gera e retorna PDF do relatorio TPV.

    GET /pdf/tpv/<uuid>/ -> download PDF relatorio TPV.

    Busca SimulacaoTPV pelo UUID com filtro de organization (multi-tenant).
    """

    def get(self, request, uuid):
        """Gera PDF do relatorio TPV e retorna como download."""
        simulacao = SimulacaoTPV.objects.filter(organization=request.organization, id=uuid).first()
        if not simulacao:
            raise Http404("Simulacao nao encontrada.")

        context = {
            "nome_contribuinte": simulacao.nome_contribuinte,
            "cpf_cnpj": simulacao.cpf_cnpj,
            **(simulacao.resultado or {}),
        }
        pdf_bytes = gerar_pdf("tpv_relatorio.html", context)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="tpv_{uuid}.pdf"'
        return response
