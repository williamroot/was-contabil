"""Testes do serviço comparador de modalidades (Capacidade de Pagamento vs TPV).

TDD rigoroso — testes escritos ANTES da implementação do service.
Cada teste valida a lógica de comparação entre as duas modalidades de transação.
Todos os valores financeiros em Decimal.

Feature exclusiva WAS Contábil (não existe nas plataformas HPR).

References:
    - Lei 13.988/2020 (transação por capacidade de pagamento — CAPAG).
    - Edital PGDAU 11/2025 (transação de pequeno valor — TPV).
"""

from decimal import Decimal

from apps.comparador.service import ComparacaoResult, comparar_modalidades
from apps.transacao.constants import ClassificacaoCredito


class TestComparador:
    """Testa comparar_modalidades() — comparação lado a lado CAPAG vs TPV.

    A função recebe os parâmetros do contribuinte e retorna qual modalidade
    oferece maior economia, com valores detalhados de ambas.
    """

    def test_tpv_melhor_para_divida_pequena_classificacao_a(self):
        """R$50k, ME/EPP, classif A (sem desconto CAPAG), TPV elegível → TPV vence.

        CAPAG classif A = 0% desconto → paga o valor integral (R$50.000).
        TPV melhor faixa = 50% desconto sobre saldo após entrada de 5%.
        TPV: entrada=2.500 + saldo_final=23.750 = R$26.250 (economia R$23.750).
        Logo TPV é melhor.
        """
        resultado = comparar_modalidades(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.A,
            tpv_elegivel=True,
        )

        assert isinstance(resultado, ComparacaoResult)
        assert resultado.recomendacao == "TPV"
        assert resultado.tpv_disponivel is True
        assert resultado.tpv_melhor_valor_final == Decimal("26250")
        assert resultado.capacidade_valor_final == Decimal("50000")

    def test_capacidade_unica_opcao_divida_grande(self):
        """R$500k, demais, classif D, TPV não elegível → só CAPACIDADE disponível.

        Quando TPV não é elegível, a única opção é Capacidade de Pagamento.
        CAPAG classif D demais = 65% desconto → paga R$175.000.
        """
        resultado = comparar_modalidades(
            valor_total=Decimal("500000"),
            percentual_previdenciario=Decimal("0.20"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
            tpv_elegivel=False,
        )

        assert resultado.recomendacao == "CAPACIDADE"
        assert resultado.tpv_disponivel is False
        assert resultado.capacidade_valor_final == Decimal("175000")
        assert resultado.capacidade_economia == Decimal("325000")

    def test_capacidade_melhor_quando_desconto_alto(self):
        """R$100k, demais, classif D, TPV elegível → CAPACIDADE vence (65% > 50%).

        CAPAG classif D demais = 65% desconto → paga R$35.000.
        TPV melhor faixa = 50% sobre saldo após 5% entrada → paga R$52.500.
        CAPACIDADE é melhor (R$35.000 < R$52.500).
        """
        resultado = comparar_modalidades(
            valor_total=Decimal("100000"),
            percentual_previdenciario=Decimal("0.30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
            tpv_elegivel=True,
        )

        assert resultado.recomendacao == "CAPACIDADE"
        assert resultado.tpv_disponivel is True
        assert resultado.capacidade_valor_final == Decimal("35000")
        assert resultado.tpv_melhor_valor_final == Decimal("52500")
        assert resultado.economia_diferenca == Decimal("17500")

    def test_resultado_contem_ambos_valores(self):
        """Resultado deve conter todos os campos de ambas as modalidades.

        Quando ambas estão disponíveis, o resultado contém:
        - tpv_disponivel, tpv_melhor_valor_final, tpv_economia
        - capacidade_valor_final, capacidade_economia
        - economia_diferenca (diferença absoluta entre os valor_final)
        """
        resultado = comparar_modalidades(
            valor_total=Decimal("80000"),
            percentual_previdenciario=Decimal("0.25"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.C,
            tpv_elegivel=True,
        )

        assert resultado.tpv_disponivel is True
        assert resultado.tpv_melhor_valor_final is not None
        assert resultado.tpv_economia is not None
        assert resultado.capacidade_valor_final is not None
        assert resultado.capacidade_economia is not None
        assert resultado.economia_diferenca is not None

        # Todos os valores monetários devem ser Decimal
        assert isinstance(resultado.tpv_melhor_valor_final, Decimal)
        assert isinstance(resultado.tpv_economia, Decimal)
        assert isinstance(resultado.capacidade_valor_final, Decimal)
        assert isinstance(resultado.capacidade_economia, Decimal)
        assert isinstance(resultado.economia_diferenca, Decimal)

    def test_tpv_indisponivel_campos_none(self):
        """Quando TPV não é elegível, campos TPV devem ser None.

        tpv_melhor_valor_final e tpv_economia são None.
        economia_diferenca é Decimal("0") (não há comparação possível).
        """
        resultado = comparar_modalidades(
            valor_total=Decimal("200000"),
            percentual_previdenciario=Decimal("0.40"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.C,
            tpv_elegivel=False,
        )

        assert resultado.tpv_disponivel is False
        assert resultado.tpv_melhor_valor_final is None
        assert resultado.tpv_economia is None
        assert resultado.recomendacao == "CAPACIDADE"
        assert resultado.economia_diferenca == Decimal("0")
