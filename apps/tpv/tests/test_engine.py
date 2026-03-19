"""Testes para engine de calculo TPV — Multi-CDA + Multi-Faixa.

Referencia legal: Edital PGDAU 11/2025 — Transacao de Pequeno Valor (TPV).
Dados de teste baseados em simulacoes reais da plataforma HPR.

TDD: estes testes devem ser escritos ANTES da implementacao.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.tpv.engine import (
    CDAInput,
    TPVInput,
    TPVMultiFaixaResult,
    TPVResult,
    calcular_tpv,
    calcular_tpv_todas_faixas,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SM = Decimal("1621")
DATA_SIM = date(2026, 3, 18)
DATA_INSCRICAO_APTA = date(2024, 1, 1)  # > 1 ano antes de DATA_SIM
DATA_INSCRICAO_RECENTE = date(2026, 1, 1)  # < 1 ano antes de DATA_SIM


def _cda(numero: str, valor: str, data_inscricao: date = DATA_INSCRICAO_APTA) -> CDAInput:
    """Helper para criar CDAInput."""
    return CDAInput(numero=numero, valor=Decimal(valor), data_inscricao=data_inscricao)


def _tpv_input(cdas: list[CDAInput], parcelas_entrada: int, parcelas_saldo: int) -> TPVInput:
    """Helper para criar TPVInput."""
    return TPVInput(
        cdas=cdas,
        parcelas_entrada=parcelas_entrada,
        parcelas_saldo=parcelas_saldo,
        salario_minimo=SM,
        data_simulacao=DATA_SIM,
    )


# ===========================================================================
# TestCalcularTPV — simulacao com CDAs individuais
# ===========================================================================


class TestCalcularTPV:
    """Testa calcular_tpv() com dados reais da plataforma HPR.

    Referencia: Edital PGDAU 11/2025 — tabela de descontos escalonados.
    Entrada: 5% em ate 5 parcelas.
    Desconto incide sobre saldo apos entrada.
    """

    def test_500_cda_1_entrada_7_parcelas(self):
        """R$500 CDA, 1 entrada, 7 parcelas -> entrada R$25, desconto 50%.

        Calculo:
        - entrada = 500 * 0.05 = 25.00
        - saldo_apos_entrada = 500 - 25 = 475.00
        - desconto 50% = 475 * 0.50 = 237.50
        - saldo_final = 475 * 0.50 = 237.50
        - parcela = 237.50 / 7 = 33.93 (ROUND_HALF_UP)
        - valor_final = 25 + 237.50 = 262.50
        - economia = 500 - 262.50 = 237.50
        """
        inp = _tpv_input(
            cdas=[_cda("CDA001", "500")],
            parcelas_entrada=1,
            parcelas_saldo=7,
        )
        result = calcular_tpv(inp)

        assert isinstance(result, TPVResult)
        assert result.total_cdas_aptas == Decimal("500")
        assert result.entrada == Decimal("25.00")
        assert result.desconto == Decimal("0.50")
        assert result.saldo == Decimal("237.50")
        assert len(result.parcelas) == 7
        assert result.parcelas[0] == Decimal("33.93")
        assert result.valor_final == Decimal("262.50")
        assert result.economia == Decimal("237.50")

    def test_500_cda_fluxo_8_parcelas(self):
        """Fluxo tem entrada (1 parcela) + saldo (7 parcelas) = 8 no total."""
        inp = _tpv_input(
            cdas=[_cda("CDA001", "500")],
            parcelas_entrada=1,
            parcelas_saldo=7,
        )
        result = calcular_tpv(inp)

        # fluxo: lista de dicts com tipo (entrada/saldo), numero, valor
        assert len(result.fluxo) == 8
        # Primeira parcela e entrada
        assert result.fluxo[0]["tipo"] == "entrada"
        assert result.fluxo[0]["valor"] == Decimal("25.00")
        # Demais sao saldo
        for item in result.fluxo[1:]:
            assert item["tipo"] == "saldo"
            assert item["valor"] == Decimal("33.93")

    def test_10000_cda_3_entrada_12_parcelas(self):
        """R$10000, 3 entrada, 12 parcelas -> desconto 45%, entrada R$500.

        Calculo:
        - entrada = 10000 * 0.05 = 500.00
        - parcela_entrada = 500.00 / 3 = 166.67 (ROUND_HALF_UP)
        - saldo_apos_entrada = 10000 - 500 = 9500.00
        - desconto 45% = 9500 * 0.45 = 4275.00
        - saldo_final = 9500 * 0.55 = 5225.00
        """
        inp = _tpv_input(
            cdas=[_cda("CDA001", "10000")],
            parcelas_entrada=3,
            parcelas_saldo=12,
        )
        result = calcular_tpv(inp)

        assert result.desconto == Decimal("0.45")
        assert result.entrada == Decimal("500.00")

    def test_80000_cda_5_entrada_55_parcelas(self):
        """R$80000, 5 entrada, 55 parcelas -> desconto 30%.

        Calculo:
        - entrada = 80000 * 0.05 = 4000.00
        - saldo_apos_entrada = 80000 - 4000 = 76000.00
        - desconto 30% = 76000 * 0.30 = 22800.00
        - saldo_final = 76000 * 0.70 = 53200.00
        """
        inp = _tpv_input(
            cdas=[_cda("CDA001", "80000")],
            parcelas_entrada=5,
            parcelas_saldo=55,
        )
        result = calcular_tpv(inp)

        assert result.desconto == Decimal("0.30")
        assert result.entrada == Decimal("4000.00")
        assert result.saldo == Decimal("53200.00")

    def test_multiplas_cdas_soma_apenas_aptas(self):
        """Multiplas CDAs: 1 apta (R$50000) + 1 nao apta (R$100000).

        Apenas CDAs aptas entram no calculo.
        R$100000 > 60 SM (R$97260) = nao apta.
        Total aptas = R$50000.
        """
        cdas = [
            _cda("CDA001", "50000"),
            _cda("CDA002", "100000"),
        ]
        inp = _tpv_input(cdas=cdas, parcelas_entrada=5, parcelas_saldo=7)
        result = calcular_tpv(inp)

        assert result.total_cdas_aptas == Decimal("50000")
        assert len(result.cdas_aptas) == 1
        assert len(result.cdas_nao_aptas) == 1
        assert result.cdas_aptas[0].numero == "CDA001"
        assert result.cdas_nao_aptas[0].numero == "CDA002"

    def test_fluxo_tipos_corretos(self):
        """Fluxo tem entrada com tipo 'entrada' e saldo com tipo 'saldo'."""
        inp = _tpv_input(
            cdas=[_cda("CDA001", "500")],
            parcelas_entrada=2,
            parcelas_saldo=7,
        )
        result = calcular_tpv(inp)

        tipos_entrada = [f for f in result.fluxo if f["tipo"] == "entrada"]
        tipos_saldo = [f for f in result.fluxo if f["tipo"] == "saldo"]
        assert len(tipos_entrada) == 2
        assert len(tipos_saldo) == 7


# ===========================================================================
# TestCalcularTPVTodasFaixas — dados HPR plataforma 3 (R$750)
# ===========================================================================


class TestCalcularTPVTodasFaixas:
    """Testa calcular_tpv_todas_faixas() com dados reais HPR plataforma 3.

    Valor original: R$750.00
    Entrada: 5% = R$37.50 em 5 parcelas de R$7.50.
    Saldo apos entrada: R$712.50.
    4 faixas de desconto aplicadas sobre saldo apos entrada.

    Referencia: Edital PGDAU 11/2025.
    """

    @pytest.fixture()
    def resultado(self) -> TPVMultiFaixaResult:
        """Resultado da simulacao multi-faixa para R$750."""
        return calcular_tpv_todas_faixas(Decimal("750"), parcelas_entrada=5)

    def test_retorna_4_faixas(self, resultado: TPVMultiFaixaResult):
        """Tabela TPV tem 4 faixas de desconto."""
        assert len(resultado.faixas) == 4

    def test_melhor_opcao_50_pct(self, resultado: TPVMultiFaixaResult):
        """Melhor opcao e a de 50% de desconto (maior economia)."""
        assert resultado.melhor_faixa.desconto_percentual == Decimal("0.50")
        assert resultado.melhor_faixa.is_melhor is True

    def test_economia_maxima(self, resultado: TPVMultiFaixaResult):
        """Economia maxima = desconto da melhor faixa = R$356.25."""
        assert resultado.economia_maxima == Decimal("356.25")

    def test_entrada_e_parcela_entrada(self, resultado: TPVMultiFaixaResult):
        """Entrada R$37.50, 5 parcelas de R$7.50."""
        assert resultado.valor_entrada == Decimal("37.50")
        assert resultado.parcela_entrada == Decimal("7.50")

    def test_saldo_apos_entrada(self, resultado: TPVMultiFaixaResult):
        """Saldo apos entrada: 750 - 37.50 = 712.50."""
        assert resultado.saldo_apos_entrada == Decimal("712.50")

    def test_faixa_50_pct(self, resultado: TPVMultiFaixaResult):
        """Faixa 50%: desconto R$356.25, saldo R$356.25, parcela R$50.89.

        - desconto = 712.50 * 0.50 = 356.25
        - saldo = 712.50 * 0.50 = 356.25
        - parcela = 356.25 / 7 = 50.89 (ROUND_HALF_UP)
        - valor_final = 37.50 + 356.25 = 393.75
        """
        faixa = resultado.faixas[0]
        assert faixa.desconto_percentual == Decimal("0.50")
        assert faixa.parcelas_max == 7
        assert faixa.desconto_valor == Decimal("356.25")
        assert faixa.saldo_final == Decimal("356.25")
        assert faixa.parcela_saldo == Decimal("50.89")
        assert faixa.valor_final == Decimal("393.75")

    def test_faixa_45_pct(self, resultado: TPVMultiFaixaResult):
        """Faixa 45%: desconto R$320.63, saldo R$391.88, parcela R$32.66.

        - desconto = 712.50 * 0.45 = 320.625 -> 320.63 (ROUND_HALF_UP)
        - saldo = 712.50 * 0.55 = 391.875 -> 391.88 (ROUND_HALF_UP)
        - parcela = 391.88 / 12 = 32.656... -> 32.66 (ROUND_HALF_UP)
        - valor_final = 37.50 + 391.88 = 429.38
        """
        faixa = resultado.faixas[1]
        assert faixa.desconto_percentual == Decimal("0.45")
        assert faixa.parcelas_max == 12
        assert faixa.desconto_valor == Decimal("320.63")
        assert faixa.saldo_final == Decimal("391.88")
        assert faixa.parcela_saldo == Decimal("32.66")
        assert faixa.valor_final == Decimal("429.38")

    def test_faixa_40_pct(self, resultado: TPVMultiFaixaResult):
        """Faixa 40%: desconto R$285.00, saldo R$427.50, parcela R$14.25.

        - desconto = 712.50 * 0.40 = 285.00
        - saldo = 712.50 * 0.60 = 427.50
        - parcela = 427.50 / 30 = 14.25
        - valor_final = 37.50 + 427.50 = 465.00
        """
        faixa = resultado.faixas[2]
        assert faixa.desconto_percentual == Decimal("0.40")
        assert faixa.parcelas_max == 30
        assert faixa.desconto_valor == Decimal("285.00")
        assert faixa.saldo_final == Decimal("427.50")
        assert faixa.parcela_saldo == Decimal("14.25")
        assert faixa.valor_final == Decimal("465.00")

    def test_faixa_30_pct(self, resultado: TPVMultiFaixaResult):
        """Faixa 30%: desconto R$213.75, saldo R$498.75, parcela R$9.07.

        - desconto = 712.50 * 0.30 = 213.75
        - saldo = 712.50 * 0.70 = 498.75
        - parcela = 498.75 / 55 = 9.068... -> 9.07 (ROUND_HALF_UP)
        - valor_final = 37.50 + 498.75 = 536.25
        """
        faixa = resultado.faixas[3]
        assert faixa.desconto_percentual == Decimal("0.30")
        assert faixa.parcelas_max == 55
        assert faixa.desconto_valor == Decimal("213.75")
        assert faixa.saldo_final == Decimal("498.75")
        assert faixa.parcela_saldo == Decimal("9.07")
        assert faixa.valor_final == Decimal("536.25")

    def test_valor_final_entrada_mais_saldo(self, resultado: TPVMultiFaixaResult):
        """valor_final de cada faixa = entrada + saldo_final."""
        for faixa in resultado.faixas:
            assert faixa.valor_final == resultado.valor_entrada + faixa.saldo_final

    def test_apenas_melhor_faixa_marcada(self, resultado: TPVMultiFaixaResult):
        """Apenas a faixa de 50% deve ter is_melhor=True."""
        melhores = [f for f in resultado.faixas if f.is_melhor]
        assert len(melhores) == 1
        assert melhores[0].desconto_percentual == Decimal("0.50")
