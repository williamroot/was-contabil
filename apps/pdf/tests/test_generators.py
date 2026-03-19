"""Testes do gerador de PDF via WeasyPrint + Django templates.

TDD rigoroso — testes escritos ANTES da implementação.
Valida que cada tipo de PDF:
1. Retorna bytes não-vazios
2. Começa com %PDF- (header válido)
3. Recebe context correto e gera sem erros

References:
    - WeasyPrint 68.x (geração PDF)
    - Django template engine (render_to_string)
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.pdf.generators import gerar_pdf

# ---------------------------------------------------------------------------
# Fixtures de contexto
# ---------------------------------------------------------------------------


@pytest.fixture
def diagnostico_context():
    """Context mínimo para template diagnostico.html."""
    return {
        "valor_original": Decimal("100000"),
        "valor_desconto": Decimal("65000"),
        "valor_com_desconto": Decimal("35000"),
        "valor_entrada": Decimal("6000"),
        "num_parcelas_entrada": 6,
        "valor_parcela_entrada": Decimal("1000"),
        "saldo_apos_entrada": Decimal("29000"),
        "classificacao": "D",
        "is_me_epp": False,
        "percentual_previdenciario": 30,
        "modalidades": [
            {
                "nome": "Previdenciário",
                "is_previdenciario": True,
                "valor": Decimal("8700"),
                "num_parcelas": 54,
                "valor_parcela": Decimal("161.11"),
                "prazo_maximo": 60,
            },
            {
                "nome": "Não Previdenciário",
                "is_previdenciario": False,
                "valor": Decimal("20300"),
                "num_parcelas": 114,
                "valor_parcela": Decimal("178.07"),
                "prazo_maximo": 120,
            },
        ],
        "fluxo": [
            {"tipo": "entrada", "valor": Decimal("1000"), "parcela": 1},
            {"tipo": "entrada", "valor": Decimal("1000"), "parcela": 2},
            {"tipo": "regular", "valor": Decimal("178.07"), "parcela": 7},
        ],
    }


@pytest.fixture
def simulacao_avancada_context():
    """Context mínimo para template simulacao_avancada_resumido/completo.html."""
    return {
        "rating": "D",
        "desconto_percentual": Decimal("0.65"),
        "desconto_total": Decimal("45500"),
        "desconto_efetivo": Decimal("45500"),
        "passivos": {
            "rfb": Decimal("50000"),
            "pgfn": Decimal("100000"),
            "total": Decimal("150000"),
            "saldo": Decimal("54500"),
        },
        "honorarios": Decimal("9100"),
        "honorarios_percentual": Decimal("0.20"),
        "previdenciario": {
            "nome": "Previdenciário",
            "componentes": {
                "principal": Decimal("20000"),
                "multa": Decimal("10000"),
                "juros": Decimal("8000"),
                "encargos": Decimal("2000"),
            },
            "desconto_result": {
                "principal_final": Decimal("20000"),
                "principal_desconto": Decimal("0"),
                "multa_final": Decimal("3500"),
                "multa_desconto": Decimal("6500"),
                "juros_final": Decimal("2800"),
                "juros_desconto": Decimal("5200"),
                "encargos_final": Decimal("700"),
                "encargos_desconto": Decimal("1300"),
                "total_desconto": Decimal("13000"),
                "total_final": Decimal("27000"),
            },
            "prazo_total": 60,
            "entrada": 6,
            "parcelas": 54,
            "saldo": Decimal("27000"),
            "fluxo": [
                {"tipo": "entrada", "valor": Decimal("270"), "parcela": 1},
            ],
        },
        "tributario": {
            "nome": "Tributário",
            "componentes": {
                "principal": Decimal("30000"),
                "multa": Decimal("15000"),
                "juros": Decimal("12000"),
                "encargos": Decimal("3000"),
            },
            "desconto_result": {
                "principal_final": Decimal("30000"),
                "principal_desconto": Decimal("0"),
                "multa_final": Decimal("5250"),
                "multa_desconto": Decimal("9750"),
                "juros_final": Decimal("4200"),
                "juros_desconto": Decimal("7800"),
                "encargos_final": Decimal("1050"),
                "encargos_desconto": Decimal("1950"),
                "total_desconto": Decimal("19500"),
                "total_final": Decimal("40500"),
            },
            "prazo_total": 120,
            "entrada": 6,
            "parcelas": 114,
            "saldo": Decimal("40500"),
            "fluxo": [
                {"tipo": "entrada", "valor": Decimal("405"), "parcela": 1},
            ],
        },
        "simples": None,
        "is_me_epp": False,
    }


@pytest.fixture
def tpv_context():
    """Context mínimo para template tpv_relatorio.html."""
    return {
        "total_cdas_aptas": Decimal("5000"),
        "cdas_aptas": [
            {
                "numero": "CDA-001",
                "valor": Decimal("3000"),
                "data_inscricao": date(2020, 3, 15),
                "validacao": {"apta": True, "motivos": []},
            },
            {
                "numero": "CDA-002",
                "valor": Decimal("2000"),
                "data_inscricao": date(2021, 6, 10),
                "validacao": {"apta": True, "motivos": []},
            },
        ],
        "cdas_nao_aptas": [
            {
                "numero": "CDA-003",
                "valor": Decimal("150000"),
                "data_inscricao": date(2025, 11, 1),
                "validacao": {
                    "apta": False,
                    "motivos": ["valor_acima_limite", "inscricao_inferior_1_ano"],
                },
            },
        ],
        "entrada": Decimal("250"),
        "desconto": Decimal("0.50"),
        "saldo": Decimal("2375"),
        "valor_final": Decimal("2625"),
        "economia": Decimal("2375"),
        "parcelas_entrada": 5,
        "valor_parcela_entrada": Decimal("50"),
        "parcelas_saldo": 7,
        "valor_parcela_saldo": Decimal("339.29"),
        "fluxo": [
            {"tipo": "entrada", "numero": 1, "valor": Decimal("50")},
            {"tipo": "entrada", "numero": 2, "valor": Decimal("50")},
            {"tipo": "saldo", "numero": 1, "valor": Decimal("339.29")},
        ],
    }


# ---------------------------------------------------------------------------
# Testes: gerar_pdf diagnostico
# ---------------------------------------------------------------------------


class TestGerarPDFDiagnostico:
    """Testa geração de PDF para diagnóstico prévio."""

    @pytest.mark.django_db
    def test_gerar_pdf_diagnostico_retorna_bytes(self, diagnostico_context):
        """PDF gerado deve retornar bytes não-vazios."""
        resultado = gerar_pdf("diagnostico.html", diagnostico_context)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    @pytest.mark.django_db
    def test_gerar_pdf_diagnostico_header_valido(self, diagnostico_context):
        """PDF gerado deve começar com %PDF- (header válido)."""
        resultado = gerar_pdf("diagnostico.html", diagnostico_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_diagnostico_data_geracao_preenchida(self, diagnostico_context):
        """PDF deve ser gerado mesmo sem data_geracao no context (auto-preenche)."""
        assert "data_geracao" not in diagnostico_context
        resultado = gerar_pdf("diagnostico.html", diagnostico_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_diagnostico_data_geracao_customizada(self, diagnostico_context):
        """PDF deve aceitar data_geracao customizada sem sobrescrever."""
        diagnostico_context["data_geracao"] = "01/01/2026 12:00"
        resultado = gerar_pdf("diagnostico.html", diagnostico_context)
        assert resultado[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Testes: gerar_pdf simulacao avancada resumido
# ---------------------------------------------------------------------------


class TestGerarPDFSimulacaoAvancadaResumido:
    """Testa geração de PDF para simulação avançada (modo resumido)."""

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_resumido_retorna_bytes(self, simulacao_avancada_context):
        """PDF gerado deve retornar bytes não-vazios."""
        resultado = gerar_pdf("simulacao_avancada_resumido.html", simulacao_avancada_context)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_resumido_header_valido(self, simulacao_avancada_context):
        """PDF gerado deve começar com %PDF- (header válido)."""
        resultado = gerar_pdf("simulacao_avancada_resumido.html", simulacao_avancada_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_resumido_com_rating(self, simulacao_avancada_context):
        """PDF deve gerar corretamente com rating badge D."""
        simulacao_avancada_context["rating"] = "D"
        resultado = gerar_pdf("simulacao_avancada_resumido.html", simulacao_avancada_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_resumido_rating_a(self, simulacao_avancada_context):
        """PDF deve gerar corretamente com rating badge A (sem desconto)."""
        simulacao_avancada_context["rating"] = "A"
        simulacao_avancada_context["desconto_percentual"] = Decimal("0")
        simulacao_avancada_context["desconto_total"] = Decimal("0")
        simulacao_avancada_context["desconto_efetivo"] = Decimal("0")
        resultado = gerar_pdf("simulacao_avancada_resumido.html", simulacao_avancada_context)
        assert resultado[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Testes: gerar_pdf simulacao avancada completo
# ---------------------------------------------------------------------------


class TestGerarPDFSimulacaoAvancadaCompleto:
    """Testa geração de PDF para simulação avançada (modo completo)."""

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_completo_retorna_bytes(self, simulacao_avancada_context):
        """PDF completo deve retornar bytes não-vazios."""
        resultado = gerar_pdf("simulacao_avancada_completo.html", simulacao_avancada_context)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_completo_header_valido(self, simulacao_avancada_context):
        """PDF completo deve começar com %PDF-."""
        resultado = gerar_pdf("simulacao_avancada_completo.html", simulacao_avancada_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_avancado_completo_com_simples(self, simulacao_avancada_context):
        """PDF completo deve gerar corretamente quando inclui Simples Nacional."""
        simulacao_avancada_context["simples"] = {
            "nome": "Simples Nacional",
            "componentes": {
                "principal": Decimal("5000"),
                "multa": Decimal("2000"),
                "juros": Decimal("1500"),
                "encargos": Decimal("500"),
            },
            "desconto_result": {
                "principal_final": Decimal("5000"),
                "principal_desconto": Decimal("0"),
                "multa_final": Decimal("700"),
                "multa_desconto": Decimal("1300"),
                "juros_final": Decimal("525"),
                "juros_desconto": Decimal("975"),
                "encargos_final": Decimal("175"),
                "encargos_desconto": Decimal("325"),
                "total_desconto": Decimal("2600"),
                "total_final": Decimal("6400"),
            },
            "prazo_total": 120,
            "entrada": 6,
            "parcelas": 114,
            "saldo": Decimal("6400"),
            "fluxo": [
                {"tipo": "entrada", "valor": Decimal("64"), "parcela": 1},
                {"tipo": "regular", "valor": Decimal("55.58"), "parcela": 7},
            ],
        }
        resultado = gerar_pdf("simulacao_avancada_completo.html", simulacao_avancada_context)
        assert resultado[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Testes: gerar_pdf TPV relatório
# ---------------------------------------------------------------------------


class TestGerarPDFTPV:
    """Testa geração de PDF para relatório TPV."""

    @pytest.mark.django_db
    def test_gerar_pdf_tpv_retorna_bytes(self, tpv_context):
        """PDF TPV deve retornar bytes não-vazios."""
        resultado = gerar_pdf("tpv_relatorio.html", tpv_context)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    @pytest.mark.django_db
    def test_gerar_pdf_tpv_header_valido(self, tpv_context):
        """PDF TPV deve começar com %PDF-."""
        resultado = gerar_pdf("tpv_relatorio.html", tpv_context)
        assert resultado[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_gerar_pdf_tpv_com_cdas(self, tpv_context):
        """PDF TPV deve gerar corretamente com CDAs aptas e não aptas."""
        resultado = gerar_pdf("tpv_relatorio.html", tpv_context)
        assert resultado[:5] == b"%PDF-"
        assert len(resultado) > 100  # PDF deve ter conteúdo substancial

    @pytest.mark.django_db
    def test_gerar_pdf_tpv_sem_cdas_nao_aptas(self, tpv_context):
        """PDF TPV deve gerar corretamente mesmo sem CDAs não aptas."""
        tpv_context["cdas_nao_aptas"] = []
        resultado = gerar_pdf("tpv_relatorio.html", tpv_context)
        assert resultado[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Testes: função gerar_pdf genérica
# ---------------------------------------------------------------------------


class TestGerarPDFGenerico:
    """Testa comportamento genérico da função gerar_pdf."""

    @pytest.mark.django_db
    def test_template_inexistente_levanta_erro(self):
        """Template inexistente deve levantar TemplateDoesNotExist."""
        from django.template.exceptions import TemplateDoesNotExist

        with pytest.raises(TemplateDoesNotExist):
            gerar_pdf("nao_existe.html", {})

    @pytest.mark.django_db
    def test_data_geracao_nao_sobrescreve_se_presente(self, diagnostico_context):
        """Se data_geracao já está no context, não deve ser sobrescrita."""
        data_custom = "15/06/2025 10:30"
        diagnostico_context["data_geracao"] = data_custom
        # gerar_pdf usa setdefault, então não sobrescreve
        gerar_pdf("diagnostico.html", diagnostico_context)
        assert diagnostico_context["data_geracao"] == data_custom
