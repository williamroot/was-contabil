"""Testes para validadores de elegibilidade CDA — módulo TPV.

Referência legal: Edital PGDAU 11/2025 — Transação de Pequeno Valor (TPV).
Elegibilidade: PF, ME, EPP — CDA <= 60 SM — inscrita há > 1 ano.

TDD: estes testes devem ser escritos ANTES da implementação.
"""

from datetime import date
from decimal import Decimal

from apps.tpv.validators import (
    CDAValidationResult,
    ElegibilidadeWizardResult,
    MotivoInaptidao,
    validar_cda,
    validar_elegibilidade_wizard,
)


class TestValidarCDAApta:
    """Testa CDA que atende todos os critérios de elegibilidade."""

    def test_cda_apta_valor_ok_e_tempo_ok(self):
        """CDA R$ 1.500, inscrita há mais de 1 ano — APTA."""
        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2024, 1, 1),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert isinstance(result, CDAValidationResult)
        assert result.apta is True
        assert result.motivos == []

    def test_cda_no_limite_exato_60sm_e_apta(self):
        """CDA no limite exato de 60 SM (R$ 97.260,00) deve ser APTA.

        SM vigente 2026: R$ 1.621,00 x 60 = R$ 97.260,00.
        Referência: Edital PGDAU 11/2025.
        """
        result = validar_cda(
            valor=Decimal("97260"),
            data_inscricao=date(2025, 3, 17),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is True
        assert result.motivos == []

    def test_cda_apta_inscricao_exatamente_365_dias(self):
        """CDA inscrita há exatamente 365 dias — APTA (limite inclusivo)."""
        result = validar_cda(
            valor=Decimal("5000"),
            data_inscricao=date(2025, 3, 18),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is True


class TestValidarCDANaoApta:
    """Testa CDAs que NÃO atendem os critérios de elegibilidade."""

    def test_cda_nao_apta_valor_acima_60sm(self):
        """CDA R$ 100.000 (acima de 60 SM) — NÃO APTA."""
        result = validar_cda(
            valor=Decimal("100000"),
            data_inscricao=date(2024, 1, 1),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is False
        assert MotivoInaptidao.VALOR_ACIMA_LIMITE in result.motivos
        assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO not in result.motivos

    def test_cda_nao_apta_inscricao_inferior_1_ano(self):
        """CDA R$ 1.500, inscrita em 15/06/2025 — NÃO APTA por tempo.

        Compatibilidade com HPR TPV Simulator:
        - Status: NÃO APTA
        - Motivo: "Inscrição inferior a 1 ano"
        - Projeção: "Apta por tempo em: 15/06/2026"
        - Dias restantes: 89
        """
        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2025, 6, 15),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is False
        assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO in result.motivos
        assert MotivoInaptidao.VALOR_ACIMA_LIMITE not in result.motivos

    def test_cda_nao_apta_ambos_motivos(self):
        """CDA R$ 200.000, inscrita há 6 meses — NÃO APTA por ambos motivos."""
        result = validar_cda(
            valor=Decimal("200000"),
            data_inscricao=date(2025, 9, 18),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is False
        assert MotivoInaptidao.VALOR_ACIMA_LIMITE in result.motivos
        assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO in result.motivos
        assert len(result.motivos) == 2


class TestProjecaoElegibilidade:
    """Testa projeção de elegibilidade futura por tempo."""

    def test_projecao_data_elegibilidade(self):
        """CDA inscrita em 15/06/2025, simulação em 18/03/2026.

        Data de elegibilidade: 15/06/2026 (1 ano após inscrição).
        """
        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2025, 6, 15),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.data_elegibilidade_tempo == date(2026, 6, 15)

    def test_projecao_dias_restantes(self):
        """CDA inscrita em 15/06/2025, simulação em 18/03/2026.

        Dias restantes: 89 (de 18/03/2026 até 15/06/2026).
        Compatibilidade com HPR TPV Simulator.
        """
        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2025, 6, 15),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.dias_restantes_tempo == 89

    def test_cda_apta_sem_projecao_tempo(self):
        """CDA já apta por tempo — data_elegibilidade_tempo é None ou no passado,
        e dias_restantes_tempo é 0.
        """
        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2024, 1, 1),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is True
        assert result.dias_restantes_tempo == 0


class TestValidarElegibilidadeWizard:
    """Testa o wizard simplificado de elegibilidade TPV.

    Compatibilidade com HPR PGFN Debt Solve (pgfn-debt-solve.base44.app).
    """

    def test_wizard_elegivel(self):
        """ME, sem CDA >60SM, R$750, >1 ano — Elegível."""
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="ME",
            possui_cda_acima_limite=False,
            valor_total=Decimal("750"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert isinstance(result, ElegibilidadeWizardResult)
        assert result.elegivel is True
        assert all(c["status"] == "ok" for c in result.criterios)
        assert result.mensagem == "Elegível para Transação de Pequeno Valor"

    def test_wizard_nao_elegivel_cda_acima_limite(self):
        """PF, com CDA >60SM — Não elegível.

        Critério "Limite por CDA" deve estar como "fail".
        """
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="PF",
            possui_cda_acima_limite=True,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert result.elegivel is False
        assert result.criterios[1]["status"] == "fail"
        assert "60 salários mínimos" in result.criterios[1]["detalhe"]

    def test_wizard_nao_elegivel_tipo_contribuinte_invalido(self):
        """Contribuinte tipo 'PJ Grande' não é elegível para TPV."""
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="PJ",
            possui_cda_acima_limite=False,
            valor_total=Decimal("750"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert result.elegivel is False
        assert result.criterios[0]["status"] == "fail"

    def test_wizard_nao_elegivel_cdas_menos_1_ano(self):
        """Todas CDAs com menos de 1 ano — Não elegível."""
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="EPP",
            possui_cda_acima_limite=False,
            valor_total=Decimal("750"),
            todas_cdas_mais_1_ano=False,
            salario_minimo=Decimal("1621"),
        )

        assert result.elegivel is False
        assert result.criterios[2]["status"] == "fail"

    def test_wizard_criterios_tem_3_itens(self):
        """Wizard deve retornar exatamente 3 critérios: tipo, limite CDA, tempo."""
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="PF",
            possui_cda_acima_limite=False,
            valor_total=Decimal("750"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert len(result.criterios) == 3
