"""Testes para constantes legais do módulo TPV.

Referência legal: Edital PGDAU 11/2025 — Transação de Pequeno Valor (TPV).
TDD: estes testes devem ser escritos ANTES da implementação.
"""

from decimal import Decimal

import pytest

from apps.tpv.constants import (
    ENTRADA_PARCELAS_MAX_TPV,
    ENTRADA_PERCENTUAL_TPV,
    LIMITE_SM_POR_CDA,
    SALARIO_MINIMO_2026,
    TABELA_DESCONTOS_TPV,
    TEMPO_MINIMO_INSCRICAO_DIAS,
    calcular_limite_valor_cda,
    get_desconto_por_parcelas,
)


class TestConstantesTPV:
    """Testa que as constantes estão definidas conforme o Edital PGDAU 11/2025."""

    def test_entrada_percentual_tpv(self):
        """Entrada de 5% do valor total — Edital PGDAU 11/2025."""
        assert ENTRADA_PERCENTUAL_TPV == Decimal("0.05")

    def test_entrada_parcelas_max_tpv(self):
        """Entrada em até 5 parcelas — Edital PGDAU 11/2025."""
        assert ENTRADA_PARCELAS_MAX_TPV == 5

    def test_limite_sm_por_cda(self):
        """CDA elegível até 60 salários mínimos — Edital PGDAU 11/2025."""
        assert LIMITE_SM_POR_CDA == 60

    def test_tempo_minimo_inscricao_dias(self):
        """CDA deve estar inscrita há mais de 1 ano (365 dias) — Edital PGDAU 11/2025."""
        assert TEMPO_MINIMO_INSCRICAO_DIAS == 365

    def test_salario_minimo_2026(self):
        """Salário mínimo vigente 2026: R$ 1.621,00."""
        assert SALARIO_MINIMO_2026 == Decimal("1621")


class TestTabelaDescontosTPV:
    """Testa a tabela de descontos escalonados — Edital PGDAU 11/2025.

    Faixas: 50% (7x), 45% (12x), 40% (30x), 30% (55x).
    Desconto incide sobre TODO o saldo (inclusive principal — exceção legal TPV).
    """

    def test_tabela_tem_4_faixas(self):
        assert len(TABELA_DESCONTOS_TPV) == 4

    def test_faixa_50_pct_7_parcelas(self):
        faixa = TABELA_DESCONTOS_TPV[0]
        assert faixa["desconto"] == Decimal("0.50")
        assert faixa["parcelas"] == 7

    def test_faixa_45_pct_12_parcelas(self):
        faixa = TABELA_DESCONTOS_TPV[1]
        assert faixa["desconto"] == Decimal("0.45")
        assert faixa["parcelas"] == 12

    def test_faixa_40_pct_30_parcelas(self):
        faixa = TABELA_DESCONTOS_TPV[2]
        assert faixa["desconto"] == Decimal("0.40")
        assert faixa["parcelas"] == 30

    def test_faixa_30_pct_55_parcelas(self):
        faixa = TABELA_DESCONTOS_TPV[3]
        assert faixa["desconto"] == Decimal("0.30")
        assert faixa["parcelas"] == 55

    def test_faixas_ordenadas_maior_desconto_primeiro(self):
        """Faixas devem estar ordenadas do maior desconto para o menor."""
        descontos = [f["desconto"] for f in TABELA_DESCONTOS_TPV]
        assert descontos == sorted(descontos, reverse=True)


class TestGetDescontoPorParcelas:
    """Testa get_desconto_por_parcelas() para cada faixa do Edital PGDAU 11/2025."""

    def test_7_parcelas_retorna_50_pct(self):
        assert get_desconto_por_parcelas(7) == Decimal("0.50")

    def test_12_parcelas_retorna_45_pct(self):
        assert get_desconto_por_parcelas(12) == Decimal("0.45")

    def test_30_parcelas_retorna_40_pct(self):
        assert get_desconto_por_parcelas(30) == Decimal("0.40")

    def test_55_parcelas_retorna_30_pct(self):
        assert get_desconto_por_parcelas(55) == Decimal("0.30")

    def test_parcelas_invalidas_levanta_erro(self):
        """Número de parcelas que não corresponde a nenhuma faixa deve levantar ValueError."""
        with pytest.raises(ValueError):
            get_desconto_por_parcelas(10)

    def test_parcelas_zero_levanta_erro(self):
        with pytest.raises(ValueError):
            get_desconto_por_parcelas(0)


class TestCalcularLimiteValorCDA:
    """Testa calcular_limite_valor_cda() — limite máximo de valor por CDA."""

    def test_limite_com_sm_2026(self):
        """60 × R$ 1.621,00 = R$ 97.260,00."""
        assert calcular_limite_valor_cda(Decimal("1621")) == Decimal("97260")

    def test_limite_com_sm_customizado(self):
        """60 × R$ 1.500,00 = R$ 90.000,00."""
        assert calcular_limite_valor_cda(Decimal("1500")) == Decimal("90000")

    def test_limite_sem_argumento_usa_sm_2026(self):
        """Sem argumento, usa SALARIO_MINIMO_2026 como padrão."""
        assert calcular_limite_valor_cda() == Decimal("97260")
