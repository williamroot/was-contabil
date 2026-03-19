"""Testes de edge cases do engine TPV — Transacao de Pequeno Valor.

Cobre cenarios extremos: zero CDAs aptas, todas CDAs nao aptas,
CDA no limite de 60 SM, CDA inscrita exatamente 365 dias,
e salario minimo diferente (historico).

Cada teste valida funcoes puras (sem Django, sem I/O, sem banco).
"""

from datetime import date, timedelta
from decimal import Decimal

from apps.tpv.constants import (
    LIMITE_SM_POR_CDA,
    SALARIO_MINIMO_2026,
    calcular_limite_valor_cda,
)
from apps.tpv.engine import CDAInput, TPVInput, calcular_tpv, calcular_tpv_todas_faixas
from apps.tpv.validators import MotivoInaptidao, validar_cda


class TestZeroCDAsAptas:
    """Testa quando nenhuma CDA eh apta."""

    def test_todas_cdas_acima_limite(self):
        """CDAs com valor acima de 60 SM sao todas nao aptas."""
        sm = Decimal("1621")
        valor_acima = calcular_limite_valor_cda(sm) + Decimal("1")

        cdas = [
            CDAInput(
                numero="CDA-001",
                valor=valor_acima,
                data_inscricao=date(2024, 1, 1),
            ),
        ]
        inp = TPVInput(
            cdas=cdas,
            parcelas_entrada=5,
            parcelas_saldo=7,
            salario_minimo=sm,
            data_simulacao=date(2026, 3, 1),
        )
        resultado = calcular_tpv(inp)

        assert len(resultado.cdas_aptas) == 0
        assert len(resultado.cdas_nao_aptas) == 1
        assert resultado.total_cdas_aptas == Decimal("0")

    def test_todas_cdas_inscricao_recente(self):
        """CDAs inscritas ha menos de 365 dias sao nao aptas."""
        sm = Decimal("1621")
        data_recente = date(2026, 3, 1) - timedelta(days=200)

        cdas = [
            CDAInput(
                numero="CDA-001",
                valor=Decimal("50000"),
                data_inscricao=data_recente,
            ),
        ]
        inp = TPVInput(
            cdas=cdas,
            parcelas_entrada=5,
            parcelas_saldo=7,
            salario_minimo=sm,
            data_simulacao=date(2026, 3, 1),
        )
        resultado = calcular_tpv(inp)

        assert len(resultado.cdas_aptas) == 0
        assert len(resultado.cdas_nao_aptas) == 1


class TestCDAExatamente60SM:
    """Testa CDA com valor exatamente no limite de 60 SM."""

    def test_valor_exato_60_sm_apta(self):
        """CDA com valor = 60 x SM eh apta (limite inclusivo)."""
        sm = Decimal("1621")
        valor_exato = calcular_limite_valor_cda(sm)

        resultado = validar_cda(
            valor=valor_exato,
            data_inscricao=date(2024, 1, 1),
            data_simulacao=date(2026, 3, 1),
            salario_minimo=sm,
        )
        assert resultado.apta is True
        assert len(resultado.motivos) == 0

    def test_valor_1_centavo_acima_60_sm_inapta(self):
        """CDA com valor = 60 x SM + 0.01 eh inapta."""
        sm = Decimal("1621")
        valor_acima = calcular_limite_valor_cda(sm) + Decimal("0.01")

        resultado = validar_cda(
            valor=valor_acima,
            data_inscricao=date(2024, 1, 1),
            data_simulacao=date(2026, 3, 1),
            salario_minimo=sm,
        )
        assert resultado.apta is False
        assert MotivoInaptidao.VALOR_ACIMA_LIMITE in resultado.motivos


class TestCDAInscritaExatamente365Dias:
    """Testa CDA inscrita exatamente no limite de 365 dias."""

    def test_inscrita_exatamente_365_dias_apta(self):
        """CDA inscrita ha exatamente 365 dias eh apta (limite inclusivo)."""
        data_sim = date(2026, 3, 1)
        data_inscricao = data_sim - timedelta(days=365)

        resultado = validar_cda(
            valor=Decimal("50000"),
            data_inscricao=data_inscricao,
            data_simulacao=data_sim,
            salario_minimo=Decimal("1621"),
        )
        assert resultado.apta is True

    def test_inscrita_364_dias_inapta(self):
        """CDA inscrita ha 364 dias eh inapta (1 dia faltando)."""
        data_sim = date(2026, 3, 1)
        data_inscricao = data_sim - timedelta(days=364)

        resultado = validar_cda(
            valor=Decimal("50000"),
            data_inscricao=data_inscricao,
            data_simulacao=data_sim,
            salario_minimo=Decimal("1621"),
        )
        assert resultado.apta is False
        assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO in resultado.motivos
        assert resultado.dias_restantes_tempo == 1

    def test_inscrita_366_dias_apta(self):
        """CDA inscrita ha 366 dias eh apta (alem do limite)."""
        data_sim = date(2026, 3, 1)
        data_inscricao = data_sim - timedelta(days=366)

        resultado = validar_cda(
            valor=Decimal("50000"),
            data_inscricao=data_inscricao,
            data_simulacao=data_sim,
            salario_minimo=Decimal("1621"),
        )
        assert resultado.apta is True
        assert resultado.dias_restantes_tempo == 0


class TestSalarioMinimoDiferente:
    """Testa calculo com salario minimo diferente (historico)."""

    def test_sm_1412_limite_84720(self):
        """SM R$ 1.412,00 (2024): limite = 60 x 1412 = R$ 84.720,00."""
        sm = Decimal("1412")
        limite = calcular_limite_valor_cda(sm)
        assert limite == Decimal("84720")

    def test_sm_1320_limite_79200(self):
        """SM R$ 1.320,00 (2023): limite = 60 x 1320 = R$ 79.200,00."""
        sm = Decimal("1320")
        limite = calcular_limite_valor_cda(sm)
        assert limite == Decimal("79200")

    def test_sm_1621_limite_97260(self):
        """SM R$ 1.621,00 (2026): limite = 60 x 1621 = R$ 97.260,00."""
        sm = Decimal("1621")
        limite = calcular_limite_valor_cda(sm)
        assert limite == Decimal("97260")

    def test_sm_padrao_quando_none(self):
        """Quando salario_minimo=None, usa SM 2026 (R$ 1.621,00)."""
        limite = calcular_limite_valor_cda(None)
        assert limite == LIMITE_SM_POR_CDA * SALARIO_MINIMO_2026


class TestCalcularTPVTodasFaixas:
    """Testa calcular_tpv_todas_faixas com cenarios diversos."""

    def test_quatro_faixas(self):
        """Resultado deve ter 4 faixas de desconto."""
        resultado = calcular_tpv_todas_faixas(Decimal("50000"))
        assert len(resultado.faixas) == 4

    def test_melhor_faixa_eh_50_porcento(self):
        """Melhor faixa deve ser a de 50% (maior desconto)."""
        resultado = calcular_tpv_todas_faixas(Decimal("50000"))
        assert resultado.melhor_faixa.desconto_percentual == Decimal("0.50")
        assert resultado.melhor_faixa.is_melhor is True

    def test_entrada_5_porcento(self):
        """Entrada eh 5% do valor total."""
        valor = Decimal("100000")
        resultado = calcular_tpv_todas_faixas(valor)
        assert resultado.valor_entrada == Decimal("5000.00")

    def test_economia_maxima_positiva(self):
        """Economia maxima deve ser positiva."""
        resultado = calcular_tpv_todas_faixas(Decimal("50000"))
        assert resultado.economia_maxima > Decimal("0")


class TestMisturaAptasNaoAptas:
    """Testa mix de CDAs aptas e nao aptas."""

    def test_uma_apta_uma_nao_apta(self):
        """Resultado deve separar CDAs aptas de nao aptas."""
        sm = Decimal("1621")
        limite = calcular_limite_valor_cda(sm)

        cdas = [
            CDAInput(
                numero="CDA-APTA",
                valor=Decimal("50000"),
                data_inscricao=date(2024, 1, 1),
            ),
            CDAInput(
                numero="CDA-NAO-APTA",
                valor=limite + Decimal("1"),
                data_inscricao=date(2024, 1, 1),
            ),
        ]
        inp = TPVInput(
            cdas=cdas,
            parcelas_entrada=5,
            parcelas_saldo=7,
            salario_minimo=sm,
            data_simulacao=date(2026, 3, 1),
        )
        resultado = calcular_tpv(inp)

        assert len(resultado.cdas_aptas) == 1
        assert len(resultado.cdas_nao_aptas) == 1
        assert resultado.cdas_aptas[0].numero == "CDA-APTA"
        assert resultado.cdas_nao_aptas[0].numero == "CDA-NAO-APTA"
        assert resultado.total_cdas_aptas == Decimal("50000")
