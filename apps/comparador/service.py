"""Serviço comparador de modalidades — Capacidade de Pagamento (CAPAG) vs TPV.

Compara lado a lado as duas modalidades de transação tributária disponíveis
para o contribuinte, recomendando a opção de maior economia.

Feature exclusiva WAS Contábil (não existe nas plataformas HPR).

Módulo Python puro — sem Django, sem I/O, sem banco.
Todos os valores financeiros em Decimal com ROUND_HALF_UP.

Lógica de comparação:
    1. Calcula o valor final pela Capacidade de Pagamento (CAPAG):
       - Aplica desconto conforme classificação (A/B=0%, C/D=65% geral ou 70% ME/EPP)
       - Valor final = valor_total - desconto
    2. Calcula o valor final pelo TPV (se elegível):
       - Entrada de 5% + melhor faixa de desconto (50% em 7 parcelas)
       - Valor final = entrada + saldo_após_desconto
    3. Compara os dois valores finais e recomenda o menor.

References:
    - Lei 13.988/2020 (transação por capacidade de pagamento).
    - Edital PGDAU 11/2025 (transação de pequeno valor — TPV).
    - Portaria PGFN 6.757/2022 (classificação CAPAG e descontos).
"""

from dataclasses import dataclass
from decimal import Decimal

from apps.core.decimal_utils import round_decimal as _round
from apps.tpv.engine import calcular_tpv_todas_faixas
from apps.transacao.constants import ClassificacaoCredito, get_desconto_por_classificacao

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparacaoResult:
    """Resultado da comparação entre Capacidade de Pagamento (CAPAG) e TPV.

    Contém os valores finais de ambas as modalidades (quando disponíveis),
    a recomendação de qual é mais vantajosa e a diferença de economia.

    Attributes:
        tpv_disponivel: True se o contribuinte é elegível para TPV.
        tpv_melhor_valor_final: Valor final pago via TPV (melhor faixa).
            None se TPV não elegível.
        tpv_economia: Economia obtida via TPV (valor_total - valor_final_tpv).
            None se TPV não elegível.
        capacidade_valor_final: Valor final pago via Capacidade de Pagamento.
        capacidade_economia: Economia obtida via CAPAG (valor_total - valor_final).
        recomendacao: "TPV" ou "CAPACIDADE" — modalidade mais vantajosa.
        economia_diferenca: Diferença absoluta entre os valores finais.
            Decimal("0") se TPV não disponível.
    """

    tpv_disponivel: bool
    tpv_melhor_valor_final: Decimal | None
    tpv_economia: Decimal | None
    capacidade_valor_final: Decimal
    capacidade_economia: Decimal
    recomendacao: str
    economia_diferenca: Decimal


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def comparar_modalidades(
    valor_total: Decimal,
    percentual_previdenciario: Decimal,
    is_me_epp: bool,
    classificacao: ClassificacaoCredito,
    tpv_elegivel: bool,
) -> ComparacaoResult:
    """Compara as modalidades Capacidade de Pagamento (CAPAG) e TPV.

    Calcula o valor final que o contribuinte pagaria em cada modalidade
    e recomenda a mais econômica. A comparação usa o valor final total
    (entrada + saldo com desconto) como critério.

    Lógica:
        - CAPAG: aplica desconto conforme classificação CAPAG sobre o valor total.
          Valor final = valor_total - desconto_capag.
        - TPV: entrada de 5% + melhor faixa de desconto (50% sobre saldo).
          Valor final = entrada_tpv + saldo_com_desconto_tpv.
        - Se ambas disponíveis, recomenda a de menor valor final.
        - Se apenas CAPAG disponível (TPV não elegível), recomenda CAPACIDADE.

    Args:
        valor_total: Valor consolidado total da dívida.
        percentual_previdenciario: Fração (0 a 1) do valor que é previdenciário.
            Usado apenas internamente pelo CAPAG; não afeta a comparação direta.
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.
        classificacao: Classificação CAPAG do crédito (A, B, C ou D).
        tpv_elegivel: True se o contribuinte é elegível para TPV.

    Returns:
        ComparacaoResult com valores de ambas as modalidades e recomendação.

    References:
        - Lei 13.988/2020, art. 11, par. 2, II (desconto CAPAG 65% geral).
        - Lei 13.988/2020, art. 11, par. 3 (desconto CAPAG 70% ME/EPP).
        - Edital PGDAU 11/2025 (desconto TPV até 50%).
        - Portaria PGFN 6.757/2022, arts. 21-25 (classificação CAPAG).
    """
    # --- 1. Calcular Capacidade de Pagamento (CAPAG) ---
    percentual_desconto = get_desconto_por_classificacao(classificacao, is_me_epp)
    desconto_capag = _round(valor_total * percentual_desconto)
    capacidade_valor_final = _round(valor_total - desconto_capag)
    capacidade_economia = desconto_capag

    # --- 2. Calcular TPV (se elegível) ---
    if tpv_elegivel:
        tpv_result = calcular_tpv_todas_faixas(valor_total)
        tpv_melhor_valor_final = tpv_result.melhor_faixa.valor_final
        tpv_economia = _round(valor_total - tpv_melhor_valor_final)
    else:
        tpv_melhor_valor_final = None
        tpv_economia = None

    # --- 3. Comparar e recomendar ---
    if not tpv_elegivel or tpv_melhor_valor_final is None:
        recomendacao = "CAPACIDADE"
        economia_diferenca = Decimal("0")
    elif capacidade_valor_final <= tpv_melhor_valor_final:
        recomendacao = "CAPACIDADE"
        economia_diferenca = _round(tpv_melhor_valor_final - capacidade_valor_final)
    else:
        recomendacao = "TPV"
        economia_diferenca = _round(capacidade_valor_final - tpv_melhor_valor_final)

    return ComparacaoResult(
        tpv_disponivel=tpv_elegivel,
        tpv_melhor_valor_final=tpv_melhor_valor_final,
        tpv_economia=tpv_economia,
        capacidade_valor_final=capacidade_valor_final,
        capacidade_economia=capacidade_economia,
        recomendacao=recomendacao,
        economia_diferenca=economia_diferenca,
    )
