"""Engine de cálculo básico para diagnóstico prévio de transação tributária (PGFN).

Engine puramente funcional — Python puro, sem Django, sem I/O, sem banco.
Todos os valores financeiros em Decimal com arredondamento ROUND_HALF_UP.
Cada resultado inclui ``_calculo_detalhes`` com passos, fórmulas e referências legais.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from dataclasses import dataclass, field
from decimal import Decimal

from apps.core.decimal_utils import round_decimal as _round
from apps.transacao.constants import (
    ENTRADA_PARCELAS_GERAL,
    ENTRADA_PARCELAS_ME_EPP,
    ENTRADA_PERCENTUAL,
    PARCELA_MINIMA_DEMAIS,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
    ClassificacaoCredito,
    get_desconto_por_classificacao,
    get_prazo_parcelas_restantes,
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiagnosticoInput:
    """Dados de entrada para o diagnóstico prévio de transação tributária.

    Attributes:
        valor_total: Valor consolidado total da dívida (sem descontos).
        percentual_previdenciario: Fração (0 a 1) do valor que é previdenciário.
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.
        classificacao: Classificação CAPAG do crédito (A, B, C ou D).
    """

    valor_total: Decimal
    percentual_previdenciario: Decimal
    is_me_epp: bool
    classificacao: ClassificacaoCredito


@dataclass
class ModalidadeResult:
    """Resultado do cálculo de uma modalidade (previdenciário ou não previdenciário).

    Attributes:
        nome: Descrição da modalidade.
        is_previdenciario: True se é modalidade previdenciária.
        valor: Valor do saldo atribuído a esta modalidade.
        num_parcelas: Número de parcelas calculadas.
        valor_parcela: Valor de cada parcela mensal.
        prazo_maximo: Prazo máximo legal em meses (inclui entrada).
    """

    nome: str
    is_previdenciario: bool
    valor: Decimal
    num_parcelas: int
    valor_parcela: Decimal
    prazo_maximo: int


@dataclass
class DiagnosticoResult:
    """Resultado completo do diagnóstico prévio de transação tributária.

    Attributes:
        valor_original: Valor consolidado original da dívida.
        valor_desconto: Valor total do desconto aplicado.
        valor_com_desconto: Valor após aplicação do desconto.
        valor_entrada: Valor total da entrada (6% sobre valor original).
        num_parcelas_entrada: Número de parcelas da entrada.
        valor_parcela_entrada: Valor de cada parcela de entrada.
        saldo_apos_entrada: Saldo restante após dedução da entrada.
        modalidades: Lista de modalidades (prev e não prev).
        calculo_detalhes: Lista de dicts com passos, fórmulas e referências legais.
    """

    valor_original: Decimal
    valor_desconto: Decimal
    valor_com_desconto: Decimal
    valor_entrada: Decimal
    num_parcelas_entrada: int
    valor_parcela_entrada: Decimal
    saldo_apos_entrada: Decimal
    modalidades: list[ModalidadeResult] = field(default_factory=list)
    calculo_detalhes: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Funções do engine
# ---------------------------------------------------------------------------


def calcular_desconto(
    valor: Decimal,
    classificacao: ClassificacaoCredito,
    is_me_epp: bool,
) -> Decimal:
    """Calcula o valor do desconto conforme classificação CAPAG e regime do contribuinte.

    O desconto incide sobre o valor total do crédito. Classificações A e B
    (alta/média recuperação) não possuem desconto.

    Args:
        valor: Valor consolidado da dívida.
        classificacao: Classificação CAPAG (A, B, C ou D).
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.

    Returns:
        Valor absoluto do desconto (Decimal). Ex: 65000 para 65% de 100000.

    References:
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
        - Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF).
        - Portaria PGFN 6.757/2022, arts. 21-25 (classificação CAPAG).
    """
    percentual = get_desconto_por_classificacao(classificacao, is_me_epp)
    return _round(valor * percentual)


def separar_divida(
    valor_total: Decimal,
    percentual_prev: Decimal,
) -> tuple[Decimal, Decimal]:
    """Separa o valor total em previdenciário e não previdenciário.

    A separação é necessária porque contribuições previdenciárias possuem
    limite constitucional de 60 meses para parcelamento.

    Args:
        valor_total: Valor consolidado total.
        percentual_prev: Fração (0 a 1) que é previdenciária.

    Returns:
        Tupla (valor_previdenciario, valor_nao_previdenciario).

    References:
        - CF/88, art. 195, §11 (limite constitucional previdenciário).
    """
    prev = _round(valor_total * percentual_prev)
    nao_prev = _round(valor_total - prev)
    return prev, nao_prev


def calcular_entrada(
    valor_total_sem_desconto: Decimal,
    is_me_epp: bool,
) -> tuple[Decimal, int, Decimal]:
    """Calcula a entrada obrigatória de 6% do valor consolidado (sem descontos).

    A entrada não recebe aplicação de desconto e é parcelada em 6 (geral)
    ou 12 (ME/EPP/PF) vezes.

    Args:
        valor_total_sem_desconto: Valor consolidado original (antes de descontos).
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.

    Returns:
        Tupla (valor_entrada, num_parcelas, valor_parcela_entrada).

    References:
        - Portaria PGFN 6.757/2022, art. 36 (entrada 6%).
        - Portaria PGFN 6.757/2022, art. 36, §2º (12 parcelas ME/EPP).
    """
    valor_entrada = _round(valor_total_sem_desconto * ENTRADA_PERCENTUAL)
    num_parcelas = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL
    valor_parcela = _round(valor_entrada / Decimal(num_parcelas))
    return valor_entrada, num_parcelas, valor_parcela


def calcular_parcelas(
    saldo: Decimal,
    is_me_epp: bool,
    is_previdenciario: bool,
) -> tuple[int, Decimal]:
    """Calcula parcelas do saldo restante após entrada, respeitando parcela mínima.

    O número de parcelas é determinado pelo prazo legal restante (prazo total
    menos parcelas de entrada). Se o valor da parcela ficar abaixo do mínimo
    legal (R$100 para demais, R$25 para MEI), o número de parcelas é reduzido.

    Args:
        saldo: Valor restante após dedução da entrada.
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.
        is_previdenciario: True se o débito é de natureza previdenciária.

    Returns:
        Tupla (num_parcelas, valor_parcela).

    References:
        - CF/88, art. 195, §11 (limite 60 meses previdenciário).
        - Lei 13.988/2020, art. 11, §2º, III (120 meses geral).
        - Lei 13.988/2020, art. 11, §3º (145 meses ME/EPP).
        - Portaria PGFN 6.757/2022 (parcela mínima R$100 / R$25 MEI).
    """
    if saldo <= Decimal("0"):
        return 0, Decimal("0")

    parcelas_restantes = get_prazo_parcelas_restantes(is_me_epp, is_previdenciario)
    parcela_minima = PARCELA_MINIMA_DEMAIS

    valor_parcela = _round(saldo / Decimal(parcelas_restantes))

    if valor_parcela < parcela_minima:
        # Reduz o número de parcelas para respeitar a parcela mínima
        num_parcelas = int(saldo / parcela_minima)
        if num_parcelas == 0:
            num_parcelas = 1
        valor_parcela = _round(saldo / Decimal(num_parcelas))
        return num_parcelas, valor_parcela

    return parcelas_restantes, valor_parcela


def gerar_fluxo_pagamento(
    valor_parcela_entrada: Decimal,
    num_parcelas_entrada: int,
    valor_parcela_regular: Decimal,
    num_parcelas_regulares: int,
) -> list[dict]:
    """Gera o fluxo de pagamento mensal com entrada seguida de parcelas regulares.

    Args:
        valor_parcela_entrada: Valor de cada parcela de entrada.
        num_parcelas_entrada: Quantidade de parcelas de entrada.
        valor_parcela_regular: Valor de cada parcela regular (pós-entrada).
        num_parcelas_regulares: Quantidade de parcelas regulares.

    Returns:
        Lista de dicts com chaves: tipo ("entrada"/"regular"), valor, parcela.

    References:
        - Portaria PGFN 6.757/2022, art. 36 (estrutura de pagamento).
    """
    fluxo = []
    parcela_num = 1

    for _ in range(num_parcelas_entrada):
        fluxo.append(
            {
                "tipo": "entrada",
                "valor": valor_parcela_entrada,
                "parcela": parcela_num,
            }
        )
        parcela_num += 1

    for _ in range(num_parcelas_regulares):
        fluxo.append(
            {
                "tipo": "regular",
                "valor": valor_parcela_regular,
                "parcela": parcela_num,
            }
        )
        parcela_num += 1

    return fluxo


def calcular_diagnostico(inp: DiagnosticoInput) -> DiagnosticoResult:
    """Calcula o diagnóstico prévio completo de transação tributária.

    Executa todos os passos do cálculo (desconto, entrada, separação da dívida,
    parcelas por modalidade) e registra cada passo em ``calculo_detalhes``
    com fórmula e referência legal para total transparência.

    Args:
        inp: Dados de entrada (DiagnosticoInput frozen dataclass).

    Returns:
        DiagnosticoResult com todos os valores calculados e detalhes.

    References:
        - Lei 13.988/2020 (transação tributária federal).
        - Portaria PGFN 6.757/2022 (regulamentação).
        - CF/88, art. 195, §11 (limite previdenciário).
    """
    detalhes: list[dict] = []
    passo = 1

    # --- Passo 1: Desconto ---
    percentual_desconto = get_desconto_por_classificacao(inp.classificacao, inp.is_me_epp)
    valor_desconto = calcular_desconto(inp.valor_total, inp.classificacao, inp.is_me_epp)
    valor_com_desconto = _round(inp.valor_total - valor_desconto)

    regime = "ME/EPP/PF" if inp.is_me_epp else "demais contribuintes"
    pct_display = int(percentual_desconto * 100)
    ref_desconto = "Lei 13.988/2020, art. 11, §3º" if inp.is_me_epp else "Lei 13.988/2020, art. 11, §2º, II"

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Desconto de {pct_display}% sobre valor consolidado "
                f"(classificação {inp.classificacao.value}, {regime})"
            ),
            "formula": (f"R$ {inp.valor_total:,.2f} x {pct_display}% = R$ {valor_desconto:,.2f}"),
            "referencia_legal": ref_desconto,
            "valor_antes": str(inp.valor_total),
            "valor_depois": str(valor_com_desconto),
        }
    )
    passo += 1

    # --- Passo 2: Entrada ---
    valor_entrada, num_parcelas_entrada, valor_parcela_entrada = calcular_entrada(inp.valor_total, inp.is_me_epp)

    ref_entrada = "Portaria PGFN 6.757/2022, art. 36"
    if inp.is_me_epp:
        ref_entrada += ", §2º"

    detalhes.append(
        {
            "passo": passo,
            "descricao": (f"Entrada de 6% sobre valor original em {num_parcelas_entrada} parcelas ({regime})"),
            "formula": (
                f"R$ {inp.valor_total:,.2f} x 6% = R$ {valor_entrada:,.2f} "
                f"/ {num_parcelas_entrada} = R$ {valor_parcela_entrada:,.2f}/parcela"
            ),
            "referencia_legal": ref_entrada,
            "valor_antes": str(inp.valor_total),
            "valor_depois": str(valor_entrada),
        }
    )
    passo += 1

    # --- Passo 3: Saldo após entrada ---
    saldo_apos_entrada = _round(valor_com_desconto - valor_entrada)

    detalhes.append(
        {
            "passo": passo,
            "descricao": "Saldo restante após desconto e dedução da entrada",
            "formula": (f"R$ {valor_com_desconto:,.2f} - R$ {valor_entrada:,.2f} = " f"R$ {saldo_apos_entrada:,.2f}"),
            "referencia_legal": "Lei 13.988/2020, art. 11 (cálculo do saldo devedor)",
            "valor_antes": str(valor_com_desconto),
            "valor_depois": str(saldo_apos_entrada),
        }
    )
    passo += 1

    # --- Passo 4: Separação previdenciário / não previdenciário ---
    valor_prev, valor_nao_prev = separar_divida(saldo_apos_entrada, inp.percentual_previdenciario)

    pct_prev_display = int(inp.percentual_previdenciario * 100)
    pct_nao_prev_display = 100 - pct_prev_display

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Separação da dívida: {pct_prev_display}% previdenciário, "
                f"{pct_nao_prev_display}% não previdenciário"
            ),
            "formula": (
                f"Prev: R$ {saldo_apos_entrada:,.2f} x {pct_prev_display}% = "
                f"R$ {valor_prev:,.2f} | "
                f"Não prev: R$ {saldo_apos_entrada:,.2f} x {pct_nao_prev_display}% = "
                f"R$ {valor_nao_prev:,.2f}"
            ),
            "referencia_legal": "CF/88, art. 195, §11 (separação por natureza do crédito)",
            "valor_antes": str(saldo_apos_entrada),
            "valor_depois": f"prev={valor_prev}, nao_prev={valor_nao_prev}",
        }
    )
    passo += 1

    # --- Passo 5: Parcelas previdenciárias ---
    modalidades: list[ModalidadeResult] = []

    prazo_max_prev = PRAZO_MAX_PREVIDENCIARIO
    if valor_prev > Decimal("0"):
        num_parc_prev, val_parc_prev = calcular_parcelas(valor_prev, inp.is_me_epp, is_previdenciario=True)
    else:
        num_parc_prev, val_parc_prev = 0, Decimal("0")

    modalidades.append(
        ModalidadeResult(
            nome="Previdenciário",
            is_previdenciario=True,
            valor=valor_prev,
            num_parcelas=num_parc_prev,
            valor_parcela=val_parc_prev,
            prazo_maximo=prazo_max_prev,
        )
    )

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Parcelas previdenciárias: {num_parc_prev} parcelas de "
                f"R$ {val_parc_prev:,.2f} (prazo máximo {prazo_max_prev} meses)"
            ),
            "formula": (
                f"R$ {valor_prev:,.2f} / {num_parc_prev} parcelas = " f"R$ {val_parc_prev:,.2f}"
                if num_parc_prev > 0
                else "Sem débito previdenciário"
            ),
            "referencia_legal": "CF/88, art. 195, §11 (limite 60 meses previdenciário)",
            "valor_antes": str(valor_prev),
            "valor_depois": str(val_parc_prev),
        }
    )
    passo += 1

    # --- Passo 6: Parcelas não previdenciárias ---
    if inp.is_me_epp:
        prazo_max_nao_prev = PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP
    else:
        prazo_max_nao_prev = PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL

    if valor_nao_prev > Decimal("0"):
        num_parc_nao_prev, val_parc_nao_prev = calcular_parcelas(valor_nao_prev, inp.is_me_epp, is_previdenciario=False)
    else:
        num_parc_nao_prev, val_parc_nao_prev = 0, Decimal("0")

    modalidades.append(
        ModalidadeResult(
            nome="Não Previdenciário",
            is_previdenciario=False,
            valor=valor_nao_prev,
            num_parcelas=num_parc_nao_prev,
            valor_parcela=val_parc_nao_prev,
            prazo_maximo=prazo_max_nao_prev,
        )
    )

    ref_nao_prev = (
        "Lei 13.988/2020, art. 11, §3º (145 meses ME/EPP)"
        if inp.is_me_epp
        else "Lei 13.988/2020, art. 11, §2º, III (120 meses geral)"
    )
    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Parcelas não previdenciárias: {num_parc_nao_prev} parcelas de "
                f"R$ {val_parc_nao_prev:,.2f} (prazo máximo {prazo_max_nao_prev} meses)"
            ),
            "formula": (
                f"R$ {valor_nao_prev:,.2f} / {num_parc_nao_prev} parcelas = " f"R$ {val_parc_nao_prev:,.2f}"
                if num_parc_nao_prev > 0
                else "Sem débito não previdenciário"
            ),
            "referencia_legal": ref_nao_prev,
            "valor_antes": str(valor_nao_prev),
            "valor_depois": str(val_parc_nao_prev),
        }
    )

    return DiagnosticoResult(
        valor_original=inp.valor_total,
        valor_desconto=valor_desconto,
        valor_com_desconto=valor_com_desconto,
        valor_entrada=valor_entrada,
        num_parcelas_entrada=num_parcelas_entrada,
        valor_parcela_entrada=valor_parcela_entrada,
        saldo_apos_entrada=saldo_apos_entrada,
        modalidades=modalidades,
        calculo_detalhes=detalhes,
    )
