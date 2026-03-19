"""Testes de edge cases do engine basico de transacao tributaria.

Cobre cenarios extremos: valor zero, 100%/0% previdenciario,
classificacao A (sem desconto), valores muito grandes e parcela minima.

Cada teste valida funcoes puras (sem Django, sem I/O, sem banco).
"""

from decimal import Decimal

from apps.transacao.constants import ClassificacaoCredito
from apps.transacao.engine import (
    DiagnosticoInput,
    calcular_desconto,
    calcular_diagnostico,
    calcular_entrada,
    calcular_parcelas,
    separar_divida,
)


class TestValorZero:
    """Testa comportamento com valores zero ou muito baixos."""

    def test_calcular_parcelas_saldo_zero(self):
        """Saldo zero retorna 0 parcelas e valor zero."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("0"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 0
        assert valor_parcela == Decimal("0")

    def test_calcular_parcelas_saldo_negativo(self):
        """Saldo negativo retorna 0 parcelas (guard clause)."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("-100"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 0
        assert valor_parcela == Decimal("0")

    def test_desconto_valor_zero(self):
        """Desconto sobre valor zero eh zero."""
        resultado = calcular_desconto(
            valor=Decimal("0"),
            classificacao=ClassificacaoCredito.D,
            is_me_epp=False,
        )
        assert resultado == Decimal("0")

    def test_separar_divida_valor_zero(self):
        """Separar divida zero resulta em ambos zero."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("0"),
            percentual_prev=Decimal("0.30"),
        )
        assert prev == Decimal("0")
        assert nao_prev == Decimal("0")


class TestPrevidenciario100Porcento:
    """Testa cenario 100% previdenciario."""

    def test_100_porcento_previdenciario(self):
        """100% previdenciario: todo saldo vai para modalidade previdenciaria."""
        inp = DiagnosticoInput(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("1"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        mods_com_valor = [m for m in resultado.modalidades if m.valor > 0]
        assert len(mods_com_valor) == 1
        assert mods_com_valor[0].is_previdenciario is True
        assert mods_com_valor[0].prazo_maximo == 60

    def test_0_porcento_previdenciario(self):
        """0% previdenciario: todo saldo vai para nao previdenciario."""
        inp = DiagnosticoInput(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        mods_com_valor = [m for m in resultado.modalidades if m.valor > 0]
        assert len(mods_com_valor) == 1
        assert mods_com_valor[0].is_previdenciario is False
        assert mods_com_valor[0].prazo_maximo == 120


class TestClassificacaoASemDesconto:
    """Testa classificacao A — sem desconto (alta recuperacao)."""

    def test_classificacao_a_valor_com_desconto_igual_original(self):
        """Classificacao A: valor com desconto = valor original."""
        inp = DiagnosticoInput(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.50"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        resultado = calcular_diagnostico(inp)

        assert resultado.valor_desconto == Decimal("0")
        assert resultado.valor_com_desconto == Decimal("100000")

    def test_classificacao_b_sem_desconto(self):
        """Classificacao B: tambem sem desconto."""
        inp = DiagnosticoInput(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.B,
        )
        resultado = calcular_diagnostico(inp)

        assert resultado.valor_desconto == Decimal("0")
        assert resultado.valor_com_desconto == Decimal("100000")


class TestValoresMuitoGrandes:
    """Testa valores muito grandes (R$ 999.999.999)."""

    def test_valor_grande_nao_causa_overflow(self):
        """Valor de R$ 999.999.999 deve calcular sem overflow."""
        inp = DiagnosticoInput(
            valor_total=Decimal("999999999"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        assert resultado.valor_original == Decimal("999999999")
        assert resultado.valor_desconto > Decimal("0")
        assert resultado.valor_com_desconto > Decimal("0")
        assert resultado.valor_entrada > Decimal("0")
        assert len(resultado.modalidades) == 2

    def test_desconto_65_sobre_valor_grande(self):
        """65% de R$ 999.999.999 calculado corretamente."""
        resultado = calcular_desconto(
            valor=Decimal("999999999"),
            classificacao=ClassificacaoCredito.D,
            is_me_epp=False,
        )
        esperado = Decimal("649999999.35")
        assert resultado == esperado


class TestParcelaMinimaValoresPequenos:
    """Testa reducao de parcelas para respeitar parcela minima."""

    def test_saldo_pequeno_reduz_parcelas(self):
        """Saldo de R$ 500 com 114 parcelas faria R$ 4.39 < R$ 100.

        Deve reduzir para 5 parcelas de R$ 100.
        """
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("500"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert valor_parcela >= Decimal("100")
        assert num_parcelas == 5

    def test_saldo_muito_pequeno_uma_parcela(self):
        """Saldo de R$ 50 (abaixo da parcela minima): 1 parcela de R$ 50."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("50"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 1
        assert valor_parcela == Decimal("50")

    def test_saldo_exatamente_parcela_minima(self):
        """Saldo de exatamente R$ 100: 1 parcela de R$ 100."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("100"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 1
        assert valor_parcela == Decimal("100")

    def test_entrada_valor_muito_pequeno(self):
        """Entrada de 6% sobre R$ 100 = R$ 6, 6 parcelas de R$ 1."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("100"),
            is_me_epp=False,
        )
        assert valor_entrada == Decimal("6.00")
        assert num_parcelas == 6
        assert valor_parcela == Decimal("1.00")
