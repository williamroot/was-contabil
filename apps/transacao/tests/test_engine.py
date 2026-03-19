"""Testes do engine de cálculo básico para diagnóstico prévio de transação tributária.

TDD rigoroso — testes escritos ANTES da implementação do engine.
Cada teste valida uma função pura (sem Django, sem I/O, sem banco).
Todos os valores financeiros em Decimal com ROUND_HALF_UP.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from decimal import Decimal

import pytest

from apps.transacao.constants import ClassificacaoCredito
from apps.transacao.engine import (
    DiagnosticoInput,
    DiagnosticoResult,
    ModalidadeResult,
    calcular_desconto,
    calcular_diagnostico,
    calcular_entrada,
    calcular_parcelas,
    gerar_fluxo_pagamento,
    separar_divida,
)

# ---------------------------------------------------------------------------
# TestCalcularDesconto
# ---------------------------------------------------------------------------


class TestCalcularDesconto:
    """Testa calcular_desconto(valor, classificacao, is_me_epp).

    Desconto incide sobre o valor total do crédito conforme classificação CAPAG.
    """

    def test_classificacao_d_demais_65_porcento(self):
        """Classificação D, demais: 65% de R$100.000 = R$65.000."""
        resultado = calcular_desconto(
            valor=Decimal("100000"),
            classificacao=ClassificacaoCredito.D,
            is_me_epp=False,
        )
        assert resultado == Decimal("65000")

    def test_classificacao_d_me_epp_70_porcento(self):
        """Classificação D, ME/EPP: 70% de R$100.000 = R$70.000."""
        resultado = calcular_desconto(
            valor=Decimal("100000"),
            classificacao=ClassificacaoCredito.D,
            is_me_epp=True,
        )
        assert resultado == Decimal("70000")

    def test_classificacao_a_sem_desconto(self):
        """Classificação A: sem desconto (alta recuperação)."""
        resultado = calcular_desconto(
            valor=Decimal("100000"),
            classificacao=ClassificacaoCredito.A,
            is_me_epp=False,
        )
        assert resultado == Decimal("0")

    def test_classificacao_a_sem_desconto_me_epp(self):
        """Classificação A ME/EPP: sem desconto."""
        resultado = calcular_desconto(
            valor=Decimal("100000"),
            classificacao=ClassificacaoCredito.A,
            is_me_epp=True,
        )
        assert resultado == Decimal("0")

    def test_classificacao_c_demais_65_porcento(self):
        """Classificação C, demais: 65% de R$50.000 = R$32.500."""
        resultado = calcular_desconto(
            valor=Decimal("50000"),
            classificacao=ClassificacaoCredito.C,
            is_me_epp=False,
        )
        assert resultado == Decimal("32500")

    def test_classificacao_c_me_epp_70_porcento(self):
        """Classificação C, ME/EPP: 70% de R$50.000 = R$35.000."""
        resultado = calcular_desconto(
            valor=Decimal("50000"),
            classificacao=ClassificacaoCredito.C,
            is_me_epp=True,
        )
        assert resultado == Decimal("35000")

    def test_classificacao_b_sem_desconto(self):
        """Classificação B: sem desconto (média recuperação)."""
        resultado = calcular_desconto(
            valor=Decimal("200000"),
            classificacao=ClassificacaoCredito.B,
            is_me_epp=False,
        )
        assert resultado == Decimal("0")

    def test_retorna_decimal(self):
        """Resultado deve ser sempre Decimal."""
        for classificacao in ClassificacaoCredito:
            for is_me_epp in (True, False):
                resultado = calcular_desconto(
                    valor=Decimal("10000"),
                    classificacao=classificacao,
                    is_me_epp=is_me_epp,
                )
                assert isinstance(resultado, Decimal)


# ---------------------------------------------------------------------------
# TestSepararDivida
# ---------------------------------------------------------------------------


class TestSepararDivida:
    """Testa separar_divida(valor_total, percentual_prev).

    Separa o valor total em previdenciário e não previdenciário.
    """

    def test_30_porcento_previdenciario(self):
        """30% previdenciário de R$100.000 → prev=30.000, nao_prev=70.000."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("100000"),
            percentual_prev=Decimal("0.30"),
        )
        assert prev == Decimal("30000")
        assert nao_prev == Decimal("70000")

    def test_zero_porcento_previdenciario(self):
        """0% previdenciário — tudo é não previdenciário."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("100000"),
            percentual_prev=Decimal("0"),
        )
        assert prev == Decimal("0")
        assert nao_prev == Decimal("100000")

    def test_100_porcento_previdenciario(self):
        """100% previdenciário — tudo é previdenciário."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("100000"),
            percentual_prev=Decimal("1"),
        )
        assert prev == Decimal("100000")
        assert nao_prev == Decimal("0")

    def test_50_porcento_previdenciario(self):
        """50% previdenciário de R$80.000 → prev=40.000, nao_prev=40.000."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("80000"),
            percentual_prev=Decimal("0.50"),
        )
        assert prev == Decimal("40000")
        assert nao_prev == Decimal("40000")

    def test_soma_igual_valor_total(self):
        """prev + nao_prev deve ser igual ao valor_total."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("100000"),
            percentual_prev=Decimal("0.30"),
        )
        assert prev + nao_prev == Decimal("100000")

    def test_retorna_decimais(self):
        """Ambos os valores devem ser Decimal."""
        prev, nao_prev = separar_divida(
            valor_total=Decimal("100000"),
            percentual_prev=Decimal("0.30"),
        )
        assert isinstance(prev, Decimal)
        assert isinstance(nao_prev, Decimal)


# ---------------------------------------------------------------------------
# TestCalcularEntrada
# ---------------------------------------------------------------------------


class TestCalcularEntrada:
    """Testa calcular_entrada(valor_total_sem_desconto, is_me_epp).

    Entrada de 6% do valor consolidado (sem descontos), parcelada em 6 ou 12x.
    """

    def test_entrada_demais_6_parcelas(self):
        """6% de R$100.000 = R$6.000, 6 parcelas de R$1.000."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("100000"),
            is_me_epp=False,
        )
        assert valor_entrada == Decimal("6000")
        assert num_parcelas == 6
        assert valor_parcela == Decimal("1000")

    def test_entrada_me_epp_12_parcelas(self):
        """6% de R$100.000 = R$6.000, 12 parcelas de R$500."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("100000"),
            is_me_epp=True,
        )
        assert valor_entrada == Decimal("6000")
        assert num_parcelas == 12
        assert valor_parcela == Decimal("500")

    def test_entrada_valor_menor(self):
        """6% de R$10.000 = R$600, 6 parcelas de R$100 (demais)."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("10000"),
            is_me_epp=False,
        )
        assert valor_entrada == Decimal("600")
        assert num_parcelas == 6
        assert valor_parcela == Decimal("100")

    def test_entrada_parcela_arredondamento(self):
        """Parcela de entrada com valor quebrado — arredondamento ROUND_HALF_UP."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("77777"),
            is_me_epp=False,
        )
        assert valor_entrada == Decimal("4666.62")
        assert num_parcelas == 6
        # 4666.62 / 6 = 777.77
        assert valor_parcela == Decimal("777.77")

    def test_retorna_decimais(self):
        """Valores de entrada e parcela devem ser Decimal."""
        valor_entrada, num_parcelas, valor_parcela = calcular_entrada(
            valor_total_sem_desconto=Decimal("100000"),
            is_me_epp=False,
        )
        assert isinstance(valor_entrada, Decimal)
        assert isinstance(num_parcelas, int)
        assert isinstance(valor_parcela, Decimal)


# ---------------------------------------------------------------------------
# TestCalcularParcelas
# ---------------------------------------------------------------------------


class TestCalcularParcelas:
    """Testa calcular_parcelas(saldo, is_me_epp, is_previdenciario).

    Calcula parcelas do saldo restante (após entrada), respeitando parcela mínima.
    """

    def test_nao_previdenciario_demais_114_parcelas(self):
        """Saldo R$94.000 / 114 parcelas (não prev, demais) = ~R$824.56."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("94000"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 114
        assert valor_parcela == Decimal("824.56")

    def test_previdenciario_demais_54_parcelas(self):
        """Saldo R$27.000 / 54 parcelas (prev, demais) = R$500."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("27000"),
            is_me_epp=False,
            is_previdenciario=True,
        )
        assert num_parcelas == 54
        assert valor_parcela == Decimal("500")

    def test_parcela_minima_demais_respeitada(self):
        """Se saldo / parcelas < R$100, reduz número de parcelas."""
        # Saldo R$5000 / 114 parcelas = ~R$43.86 < R$100
        # Ajuste: R$5000 / R$100 = 50 parcelas
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("5000"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert valor_parcela >= Decimal("100")
        assert num_parcelas == 50

    def test_parcela_minima_mei_respeitada(self):
        """Se saldo / parcelas < R$25 (MEI), reduz número de parcelas.

        Nota: is_me_epp=True usa parcela mínima R$100 (PARCELA_MINIMA_DEMAIS).
        Apenas MEI usa R$25, mas engine básico não diferencia MEI de ME/EPP.
        Logo, parcela mínima para is_me_epp=True é R$100 (mesma dos demais).
        """
        # ME/EPP não prev: 133 parcelas restantes
        # Saldo R$5000 / 133 = ~R$37.59 < R$100
        # Ajuste: R$5000 / R$100 = 50 parcelas
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("5000"),
            is_me_epp=True,
            is_previdenciario=False,
        )
        assert valor_parcela >= Decimal("100")
        assert num_parcelas == 50

    def test_previdenciario_me_epp_48_parcelas(self):
        """ME/EPP previdenciário: 60 - 12 = 48 parcelas."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("48000"),
            is_me_epp=True,
            is_previdenciario=True,
        )
        assert num_parcelas == 48
        assert valor_parcela == Decimal("1000")

    def test_nao_previdenciario_me_epp_133_parcelas(self):
        """ME/EPP não previdenciário: 145 - 12 = 133 parcelas."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("133000"),
            is_me_epp=True,
            is_previdenciario=False,
        )
        assert num_parcelas == 133
        assert valor_parcela == Decimal("1000")

    def test_retorna_tipos_corretos(self):
        """num_parcelas é int, valor_parcela é Decimal."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("94000"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert isinstance(num_parcelas, int)
        assert isinstance(valor_parcela, Decimal)

    def test_saldo_zero_retorna_zero_parcelas(self):
        """Se saldo é zero, não há parcelas."""
        num_parcelas, valor_parcela = calcular_parcelas(
            saldo=Decimal("0"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 0
        assert valor_parcela == Decimal("0")


# ---------------------------------------------------------------------------
# TestGerarFluxoPagamento
# ---------------------------------------------------------------------------


class TestGerarFluxoPagamento:
    """Testa gerar_fluxo_pagamento com entrada + parcelas."""

    def test_fluxo_basico_entrada_e_parcelas(self):
        """Fluxo deve ter parcelas de entrada seguidas de parcelas regulares."""
        fluxo = gerar_fluxo_pagamento(
            valor_parcela_entrada=Decimal("1000"),
            num_parcelas_entrada=6,
            valor_parcela_regular=Decimal("500"),
            num_parcelas_regulares=114,
        )
        assert len(fluxo) == 120  # 6 + 114

        # Primeiras 6 parcelas são entrada
        for i in range(6):
            assert fluxo[i]["tipo"] == "entrada"
            assert fluxo[i]["valor"] == Decimal("1000")
            assert fluxo[i]["parcela"] == i + 1

        # Parcelas 7 a 120 são regulares
        for i in range(6, 120):
            assert fluxo[i]["tipo"] == "regular"
            assert fluxo[i]["valor"] == Decimal("500")
            assert fluxo[i]["parcela"] == i + 1

    def test_fluxo_somente_entrada(self):
        """Se não há parcelas regulares, fluxo tem só entrada."""
        fluxo = gerar_fluxo_pagamento(
            valor_parcela_entrada=Decimal("1000"),
            num_parcelas_entrada=6,
            valor_parcela_regular=Decimal("0"),
            num_parcelas_regulares=0,
        )
        assert len(fluxo) == 6
        for item in fluxo:
            assert item["tipo"] == "entrada"

    def test_fluxo_retorna_lista_dicts(self):
        """Cada item do fluxo deve ser um dict com tipo, valor, parcela."""
        fluxo = gerar_fluxo_pagamento(
            valor_parcela_entrada=Decimal("500"),
            num_parcelas_entrada=6,
            valor_parcela_regular=Decimal("300"),
            num_parcelas_regulares=54,
        )
        for item in fluxo:
            assert "tipo" in item
            assert "valor" in item
            assert "parcela" in item
            assert isinstance(item["valor"], Decimal)
            assert isinstance(item["parcela"], int)

    def test_fluxo_total_correto(self):
        """Soma do fluxo deve bater com entrada + parcelas regulares."""
        fluxo = gerar_fluxo_pagamento(
            valor_parcela_entrada=Decimal("1000"),
            num_parcelas_entrada=6,
            valor_parcela_regular=Decimal("824.56"),
            num_parcelas_regulares=114,
        )
        total = sum(item["valor"] for item in fluxo)
        esperado = Decimal("1000") * 6 + Decimal("824.56") * 114
        assert total == esperado


# ---------------------------------------------------------------------------
# TestDiagnosticoCompleto — dados HPR reais
# ---------------------------------------------------------------------------


class TestDiagnosticoCompleto:
    """Testa calcular_diagnostico com cenários reais da plataforma HPR.

    Cada resultado deve incluir _calculo_detalhes com passos e referências legais.
    """

    def test_10k_30prev_demais_classif_d(self):
        """R$10k, 30% prev, demais, classif D.

        Esperado:
        - Desconto 65% → valor com desconto = R$3.500
        - Entrada 6% de R$10.000 = R$600, 6 parcelas de R$100
        - Saldo = R$3.500 - R$600 = R$2.900
        - Prev: 30% de R$2.900 = R$870 / 54 parcelas
        - Não prev: 70% de R$2.900 = R$2.030 / 114 parcelas
        """
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        assert isinstance(resultado, DiagnosticoResult)
        assert resultado.valor_original == Decimal("10000")
        assert resultado.valor_desconto == Decimal("6500")
        assert resultado.valor_com_desconto == Decimal("3500")
        assert resultado.valor_entrada == Decimal("600")
        assert resultado.num_parcelas_entrada == 6
        assert resultado.valor_parcela_entrada == Decimal("100")

        # Saldo após entrada
        assert resultado.saldo_apos_entrada == Decimal("2900")

        # Modalidades (previdenciário e não previdenciário)
        assert len(resultado.modalidades) == 2

        # Verificar que tem _calculo_detalhes
        assert resultado.calculo_detalhes is not None
        assert len(resultado.calculo_detalhes) > 0

        # Cada detalhe deve ter os campos obrigatórios
        for detalhe in resultado.calculo_detalhes:
            assert "passo" in detalhe
            assert "descricao" in detalhe
            assert "referencia_legal" in detalhe

    def test_10k_30prev_me_epp_classif_d(self):
        """R$10k, 30% prev, ME/EPP, classif D.

        Esperado:
        - Desconto 70% → valor com desconto = R$3.000
        - Entrada 6% de R$10.000 = R$600, 12 parcelas de R$50
        - Prazo prev: 60 meses, prazo não prev: 145 meses
        """
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        assert resultado.valor_desconto == Decimal("7000")
        assert resultado.valor_com_desconto == Decimal("3000")
        assert resultado.valor_entrada == Decimal("600")
        assert resultado.num_parcelas_entrada == 12
        assert resultado.valor_parcela_entrada == Decimal("50")
        assert resultado.saldo_apos_entrada == Decimal("2400")

        # Verificar detalhes do cálculo
        assert len(resultado.calculo_detalhes) > 0

    def test_100k_50prev_classif_a_sem_desconto(self):
        """R$100k, 50% prev, classif A → sem desconto.

        Esperado:
        - Desconto 0% → valor com desconto = R$100.000
        - Entrada 6% de R$100.000 = R$6.000, 6 parcelas de R$1.000
        - Saldo: R$94.000
        - Prev (50%): R$47.000 / 54 parcelas
        - Não prev (50%): R$47.000 / 114 parcelas
        """
        inp = DiagnosticoInput(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.50"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        resultado = calcular_diagnostico(inp)

        assert resultado.valor_desconto == Decimal("0")
        assert resultado.valor_com_desconto == Decimal("100000")
        assert resultado.valor_entrada == Decimal("6000")
        assert resultado.num_parcelas_entrada == 6
        assert resultado.valor_parcela_entrada == Decimal("1000")
        assert resultado.saldo_apos_entrada == Decimal("94000")

        # Verificar modalidades
        assert len(resultado.modalidades) == 2

        # Previdenciário
        mod_prev = [m for m in resultado.modalidades if m.is_previdenciario][0]
        assert mod_prev.valor == Decimal("47000")
        assert mod_prev.num_parcelas == 54
        assert mod_prev.valor_parcela == Decimal("870.37")
        assert mod_prev.prazo_maximo == 60

        # Não previdenciário
        mod_nao_prev = [m for m in resultado.modalidades if not m.is_previdenciario][0]
        assert mod_nao_prev.valor == Decimal("47000")
        assert mod_nao_prev.num_parcelas == 114
        assert mod_nao_prev.valor_parcela == Decimal("412.28")
        assert mod_nao_prev.prazo_maximo == 120

        # Detalhes do cálculo
        assert len(resultado.calculo_detalhes) > 0

    def test_calculo_detalhes_tem_passos_sequenciais(self):
        """Os passos do _calculo_detalhes devem ser sequenciais (1, 2, 3...)."""
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        passos = [d["passo"] for d in resultado.calculo_detalhes]
        assert passos == list(range(1, len(passos) + 1))

    def test_calculo_detalhes_contem_referencias_legais(self):
        """Cada passo deve ter referência legal não vazia."""
        inp = DiagnosticoInput(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0.40"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.C,
        )
        resultado = calcular_diagnostico(inp)

        for detalhe in resultado.calculo_detalhes:
            assert detalhe["referencia_legal"].strip() != "", f"Passo {detalhe['passo']} sem referência legal"

    def test_calculo_detalhes_contem_formula(self):
        """Cada passo deve ter fórmula descritiva."""
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        for detalhe in resultado.calculo_detalhes:
            assert "formula" in detalhe
            assert detalhe["formula"].strip() != "", f"Passo {detalhe['passo']} sem fórmula"

    def test_diagnostico_result_eh_dataclass(self):
        """DiagnosticoResult deve ser uma dataclass."""
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)
        assert hasattr(resultado, "__dataclass_fields__")

    def test_diagnostico_input_eh_frozen(self):
        """DiagnosticoInput deve ser frozen (imutável)."""
        inp = DiagnosticoInput(
            valor_total=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        with pytest.raises(AttributeError):
            inp.valor_total = Decimal("20000")

    def test_modalidade_result_eh_dataclass(self):
        """ModalidadeResult deve ser uma dataclass."""
        inp = DiagnosticoInput(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.50"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        resultado = calcular_diagnostico(inp)
        for mod in resultado.modalidades:
            assert hasattr(mod, "__dataclass_fields__")
            assert isinstance(mod, ModalidadeResult)

    def test_somente_previdenciario(self):
        """100% previdenciário — apenas uma modalidade previdenciária com saldo."""
        inp = DiagnosticoInput(
            valor_total=Decimal("60000"),
            percentual_previdenciario=Decimal("1"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        resultado = calcular_diagnostico(inp)

        mods_com_valor = [m for m in resultado.modalidades if m.valor > 0]
        assert len(mods_com_valor) == 1
        assert mods_com_valor[0].is_previdenciario is True

    def test_somente_nao_previdenciario(self):
        """0% previdenciário — apenas uma modalidade não previdenciária com saldo."""
        inp = DiagnosticoInput(
            valor_total=Decimal("60000"),
            percentual_previdenciario=Decimal("0"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        resultado = calcular_diagnostico(inp)

        mods_com_valor = [m for m in resultado.modalidades if m.valor > 0]
        assert len(mods_com_valor) == 1
        assert mods_com_valor[0].is_previdenciario is False

    def test_valor_total_pagamento_coerente(self):
        """Total pago (entrada + parcelas) deve bater com valor_com_desconto."""
        inp = DiagnosticoInput(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        resultado = calcular_diagnostico(inp)

        total_modalidades = sum(m.valor_parcela * m.num_parcelas for m in resultado.modalidades if m.valor > 0)
        total_pago = resultado.valor_entrada + total_modalidades

        # Pode haver diferença de centavos por arredondamento
        diferenca = abs(total_pago - resultado.valor_com_desconto)
        assert diferenca <= Decimal("1"), (
            f"Diferença de R${diferenca} entre total pago ({total_pago}) "
            f"e valor com desconto ({resultado.valor_com_desconto})"
        )
