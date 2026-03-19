"""Engine avançado de simulação de transação tributária (PGFN).

Engine com decomposição Principal/Multa/Juros/Encargos, rating CAPAG automático,
3 categorias de débitos (previdenciário, tributário, simples nacional) e honorários.

Puramente funcional — Python puro, sem Django, sem I/O, sem banco.
Todos os valores financeiros em Decimal com arredondamento ROUND_HALF_UP.
Cada resultado inclui ``calculo_detalhes`` com passos, fórmulas e referências legais.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022, art. 24 (classificação CAPAG)
    - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal)
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional

from apps.core.decimal_utils import round_decimal as _round
from apps.transacao.constants import (
    DESCONTO_MAX_GERAL,
    DESCONTO_MAX_ME_EPP,
    ENTRADA_PARCELAS_GERAL,
    ENTRADA_PARCELAS_ME_EPP,
    ENTRADA_PERCENTUAL,
    PARCELA_MINIMA_DEMAIS,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RatingCAPAG(Enum):
    """Rating de capacidade de pagamento conforme Portaria PGFN 6.757/2022, art. 24.

    O rating determina o percentual de desconto aplicável na transação.

    - A: Alta recuperação (CAPAG >= 2x dívida) — sem desconto.
    - B: Média recuperação (CAPAG >= 1x dívida, < 2x) — sem desconto.
    - C: Difícil recuperação (CAPAG >= 0.5x dívida, < 1x) — desconto máximo.
    - D: Irrecuperável (CAPAG < 0.5x dívida) — desconto máximo.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DebitoComponentes:
    """Composição de um débito em 4 componentes: principal, multa, juros e encargos.

    REGRA LEGAL: O principal NUNCA recebe desconto (Lei 13.988/2020, art. 11, §2º, I).
    Apenas multa, juros e encargos são descontáveis.

    Attributes:
        principal: Montante do principal (não descontável).
        multa: Valor de multas (descontável).
        juros: Valor de juros (descontável).
        encargos: Valor de encargos legais (descontável).
    """

    principal: Decimal
    multa: Decimal
    juros: Decimal
    encargos: Decimal

    @property
    def total(self) -> Decimal:
        """Soma total dos 4 componentes."""
        return self.principal + self.multa + self.juros + self.encargos

    @property
    def descontavel(self) -> Decimal:
        """Soma dos componentes descontáveis (multa + juros + encargos, sem principal)."""
        return self.multa + self.juros + self.encargos


@dataclass(frozen=True)
class DescontoResult:
    """Resultado do cálculo de desconto por componente.

    INVARIANTE: principal_desconto é SEMPRE 0 (art. 11, §2º, I).

    Attributes:
        principal_final: Valor do principal após desconto (sempre igual ao original).
        principal_desconto: Valor descontado do principal (sempre 0).
        multa_final: Valor da multa após desconto.
        multa_desconto: Valor descontado da multa.
        juros_final: Valor dos juros após desconto.
        juros_desconto: Valor descontado dos juros.
        encargos_final: Valor dos encargos após desconto.
        encargos_desconto: Valor descontado dos encargos.
        total_desconto: Soma total dos descontos aplicados.
        total_final: Valor total após aplicação dos descontos.
    """

    principal_final: Decimal
    principal_desconto: Decimal
    multa_final: Decimal
    multa_desconto: Decimal
    juros_final: Decimal
    juros_desconto: Decimal
    encargos_final: Decimal
    encargos_desconto: Decimal
    total_desconto: Decimal
    total_final: Decimal


@dataclass(frozen=True)
class CategoriaResult:
    """Resultado do cálculo de uma categoria de débito (prev, tributário, simples).

    Attributes:
        nome: Nome da categoria (ex: "Previdenciário").
        componentes: Composição original do débito.
        desconto_result: Resultado do desconto por componente.
        prazo_total: Prazo máximo legal em meses (inclui entrada).
        entrada: Número de parcelas de entrada.
        parcelas: Número de parcelas regulares (prazo_total - entrada).
        saldo: Valor total após desconto (= desconto_result.total_final).
        fluxo: Lista de dicts com fluxo de pagamento mensal.
    """

    nome: str
    componentes: DebitoComponentes
    desconto_result: DescontoResult
    prazo_total: int
    entrada: int
    parcelas: int
    saldo: Decimal
    fluxo: list = field(default_factory=list)


@dataclass(frozen=True)
class SimulacaoAvancadaInput:
    """Dados de entrada para simulação avançada de transação tributária.

    Attributes:
        previdenciario: Débito previdenciário (Principal/Multa/Juros/Encargos).
        tributario: Débito tributário (Principal/Multa/Juros/Encargos).
        simples: Débito do simples nacional (opcional).
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.
        capag_60m: Capacidade de pagamento estimada em 60 meses.
        passivo_rfb: Passivo total junto à RFB.
        passivo_pgfn: Passivo total junto à PGFN (base para desconto).
        desconto_escolha: "MAIOR" (máximo) ou "MENOR" (metade do máximo).
        honorarios_percentual: Percentual de honorários sobre o desconto (ex: 0.20 = 20%).
        metodo_desconto: Método de cálculo do desconto.
            "CAPAG" (padrão): Saldo transacionado = CAPAG. Desconto é distribuído
            proporcionalmente sobre multa/juros/encargos de forma que o contribuinte
            pague exatamente sua capacidade de pagamento. Compatível com a HPR.
            "PERCENTUAL": Aplica o percentual fixo (65%/70%) diretamente sobre cada
            componente (multa × %, juros × %, encargos × %). Mais transparente.

    References:
        - Portaria PGFN 6.757/2022, art. 24 (princípio: saldo = CAPAG).
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
    """

    previdenciario: DebitoComponentes
    tributario: DebitoComponentes
    simples: Optional[DebitoComponentes]
    is_me_epp: bool
    capag_60m: Decimal
    passivo_rfb: Decimal
    passivo_pgfn: Decimal
    desconto_escolha: str
    honorarios_percentual: Decimal
    metodo_desconto: str = "CAPAG"


@dataclass
class SimulacaoAvancadaResult:
    """Resultado completo da simulação avançada de transação tributária.

    Attributes:
        rating: Rating CAPAG calculado (A, B, C ou D).
        desconto_percentual: Percentual de desconto aplicado (Decimal).
        desconto_total: Soma dos descontos de todas as categorias.
        desconto_efetivo: Desconto limitado ao passivo PGFN.
        previdenciario: Resultado da categoria previdenciária.
        tributario: Resultado da categoria tributária.
        simples: Resultado da categoria simples nacional (None se não informado).
        passivos: Dict com rfb, pgfn, total, saldo.
        honorarios: Valor dos honorários (percentual sobre desconto efetivo).
        calculo_detalhes: Lista de dicts com passos, fórmulas e referências legais.
    """

    rating: RatingCAPAG
    desconto_percentual: Decimal
    desconto_total: Decimal
    desconto_efetivo: Decimal
    previdenciario: CategoriaResult
    tributario: CategoriaResult
    simples: Optional[CategoriaResult]
    passivos: dict
    honorarios: Decimal
    calculo_detalhes: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Funções do engine
# ---------------------------------------------------------------------------


def calcular_rating_capag(capag: Decimal, divida: Decimal) -> RatingCAPAG:
    """Calcula o rating CAPAG conforme a Portaria PGFN 6.757/2022, art. 24.

    O rating é determinado pela relação entre a capacidade de pagamento (CAPAG)
    e a dívida consolidada total (passivo RFB + PGFN).

    Args:
        capag: Capacidade de pagamento estimada em 60 meses.
        divida: Dívida consolidada total.

    Returns:
        RatingCAPAG enum (A, B, C ou D).

    References:
        - Portaria PGFN 6.757/2022, art. 24.
    """
    if divida <= Decimal("0"):
        return RatingCAPAG.A

    ratio = capag / divida

    if ratio >= Decimal("2"):
        return RatingCAPAG.A
    if ratio >= Decimal("1"):
        return RatingCAPAG.B
    if ratio >= Decimal("0.5"):
        return RatingCAPAG.C
    return RatingCAPAG.D


def calcular_desconto_componentes(
    componentes: DebitoComponentes,
    desconto_pct: Decimal,
) -> DescontoResult:
    """Calcula o desconto sobre cada componente do débito.

    REGRA CRÍTICA: O principal NUNCA tem desconto (Lei 13.988/2020, art. 11, §2º, I).
    Desconto incide apenas sobre multa, juros e encargos.

    Args:
        componentes: DebitoComponentes com principal, multa, juros e encargos.
        desconto_pct: Percentual de desconto (Decimal, 0 a 1). Ex: Decimal("0.70").

    Returns:
        DescontoResult com valores por componente.

    Raises:
        AssertionError: Se principal_desconto for diferente de zero (invariante violada).

    References:
        - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal).
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
        - Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF).
    """
    principal_desconto = Decimal("0")
    principal_final = componentes.principal

    multa_desconto = _round(componentes.multa * desconto_pct)
    multa_final = _round(componentes.multa - multa_desconto)

    juros_desconto = _round(componentes.juros * desconto_pct)
    juros_final = _round(componentes.juros - juros_desconto)

    encargos_desconto = _round(componentes.encargos * desconto_pct)
    encargos_final = _round(componentes.encargos - encargos_desconto)

    total_desconto = _round(multa_desconto + juros_desconto + encargos_desconto)
    total_final = _round(principal_final + multa_final + juros_final + encargos_final)

    # INVARIANTE CRÍTICA: principal NUNCA tem desconto
    assert principal_desconto == Decimal("0"), (
        f"VIOLAÇÃO LEGAL: principal_desconto deve ser SEMPRE 0, "
        f"mas foi {principal_desconto}. "
        f"Lei 13.988/2020, art. 11, §2º, I veda redução do principal."
    )

    return DescontoResult(
        principal_final=principal_final,
        principal_desconto=principal_desconto,
        multa_final=multa_final,
        multa_desconto=multa_desconto,
        juros_final=juros_final,
        juros_desconto=juros_desconto,
        encargos_final=encargos_final,
        encargos_desconto=encargos_desconto,
        total_desconto=total_desconto,
        total_final=total_final,
    )


def calcular_desconto_componentes_capag(
    componentes: DebitoComponentes,
    desconto_alvo: Decimal,
) -> DescontoResult:
    """Calcula o desconto distribuído proporcionalmente para atingir o alvo (método CAPAG).

    Neste método, o desconto total é determinado PRIMEIRO (dívida - CAPAG),
    e depois distribuído proporcionalmente entre multa, juros e encargos.
    O principal NUNCA recebe desconto.

    O princípio é: Saldo Transacionado = CAPAG (capacidade de pagamento).
    Desconto = Dívida - CAPAG, limitado ao total descontável (multa+juros+encargos)
    e ao limite legal (65%/70% do total).

    Args:
        componentes: DebitoComponentes com principal, multa, juros e encargos.
        desconto_alvo: Valor total de desconto desejado (já limitado pelo caller).

    Returns:
        DescontoResult com desconto distribuído proporcionalmente.

    References:
        - Portaria PGFN 6.757/2022, art. 24 (princípio: saldo = CAPAG).
        - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal).
    """
    principal_desconto = Decimal("0")
    principal_final = componentes.principal

    descontavel = componentes.descontavel
    if descontavel <= Decimal("0") or desconto_alvo <= Decimal("0"):
        return DescontoResult(
            principal_final=principal_final,
            principal_desconto=principal_desconto,
            multa_final=componentes.multa,
            multa_desconto=Decimal("0"),
            juros_final=componentes.juros,
            juros_desconto=Decimal("0"),
            encargos_final=componentes.encargos,
            encargos_desconto=Decimal("0"),
            total_desconto=Decimal("0"),
            total_final=componentes.total,
        )

    # Limitar desconto ao total descontável
    desconto_efetivo = min(desconto_alvo, descontavel)

    # Distribuir proporcionalmente entre multa, juros e encargos
    ratio = desconto_efetivo / descontavel

    multa_desconto = _round(componentes.multa * ratio)
    juros_desconto = _round(componentes.juros * ratio)
    # Encargos pega o resto para evitar diferença de arredondamento
    encargos_desconto = _round(desconto_efetivo - multa_desconto - juros_desconto)

    multa_final = _round(componentes.multa - multa_desconto)
    juros_final = _round(componentes.juros - juros_desconto)
    encargos_final = _round(componentes.encargos - encargos_desconto)

    total_desconto = _round(multa_desconto + juros_desconto + encargos_desconto)
    total_final = _round(principal_final + multa_final + juros_final + encargos_final)

    assert principal_desconto == Decimal(
        "0"
    ), "VIOLAÇÃO LEGAL: principal_desconto deve ser SEMPRE 0. Lei 13.988/2020, art. 11, §2º, I."

    return DescontoResult(
        principal_final=principal_final,
        principal_desconto=principal_desconto,
        multa_final=multa_final,
        multa_desconto=multa_desconto,
        juros_final=juros_final,
        juros_desconto=juros_desconto,
        encargos_final=encargos_final,
        encargos_desconto=encargos_desconto,
        total_desconto=total_desconto,
        total_final=total_final,
    )


def _calcular_categoria(
    nome: str,
    componentes: DebitoComponentes,
    desconto_pct: Decimal,
    is_me_epp: bool,
    is_previdenciario: bool,
    metodo_desconto: str = "CAPAG",
    capag_60m: Decimal = Decimal("0"),
    passivo_pgfn: Decimal = Decimal("0"),
) -> CategoriaResult:
    """Calcula o resultado de uma categoria de débito.

    Args:
        nome: Nome da categoria (ex: "Previdenciário").
        componentes: Composição do débito.
        desconto_pct: Percentual de desconto.
        is_me_epp: True se contribuinte é ME/EPP/PF.
        is_previdenciario: True se a categoria é previdenciária.

    Returns:
        CategoriaResult com todos os dados da categoria.

    References:
        - CF/88, art. 195, §11 (limite 60 meses previdenciário).
        - Lei 13.988/2020, art. 11, §2º, III (120 meses geral).
        - Lei 13.988/2020, art. 11, §3º (145 meses ME/EPP).
        - Portaria PGFN 6.757/2022, art. 36 (entrada).
    """
    if metodo_desconto == "CAPAG" and passivo_pgfn > Decimal("0") and componentes.total > Decimal("0"):
        # Método CAPAG: Desconta M+J+E preservando apenas a entrada (6%).
        #
        # Fórmula verificada contra HPR Plataforma 4 (Simulação de Transação Meta):
        # desconto = descontável × (1 - ENTRADA_PERCENTUAL)
        # Ou seja: desconta 94% de M+J+E, preserva 6% para a entrada.
        #
        # Resultado: contribuinte paga Principal + 6% de M+J+E como saldo.
        # Este é o princípio da Portaria PGFN 6.757/2022: maximizar o desconto
        # respeitando que a entrada (6%) sempre é devida.
        #
        # Limites aplicados:
        # 1. Máximo legal: 65%/70% do valor total da inscrição (P+M+J+E)
        # 2. Máximo descontável: total de M+J+E (principal nunca)

        # Desconto alvo: 94% do descontável (100% - 6% entrada)
        desconto_alvo_capag = _round(componentes.descontavel * (Decimal("1") - ENTRADA_PERCENTUAL))

        # Limite legal: 65%/70% do total da inscrição
        desconto_max_legal = _round(componentes.total * desconto_pct)

        # Desconto efetivo = mínimo dos limites
        desconto_alvo = min(desconto_alvo_capag, desconto_max_legal, componentes.descontavel)

        desconto_result = calcular_desconto_componentes_capag(componentes, desconto_alvo)
    else:
        # Método PERCENTUAL: % flat sobre cada componente
        desconto_result = calcular_desconto_componentes(componentes, desconto_pct)

    if is_previdenciario:
        prazo_total = PRAZO_MAX_PREVIDENCIARIO
    elif is_me_epp:
        prazo_total = PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP
    else:
        prazo_total = PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL

    entrada_parcelas = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL
    parcelas_restantes = prazo_total - entrada_parcelas

    saldo = desconto_result.total_final

    # Gerar fluxo de pagamento
    fluxo = []
    if saldo > Decimal("0") and parcelas_restantes > 0:
        valor_entrada = _round(saldo * ENTRADA_PERCENTUAL)
        valor_parcela_entrada = _round(valor_entrada / Decimal(entrada_parcelas))

        saldo_apos_entrada = _round(saldo - valor_entrada)

        # Verificar parcela mínima
        if saldo_apos_entrada > Decimal("0"):
            valor_parcela_regular = _round(saldo_apos_entrada / Decimal(parcelas_restantes))
            num_parcelas_regular = parcelas_restantes

            if valor_parcela_regular < PARCELA_MINIMA_DEMAIS:
                num_parcelas_regular = int(saldo_apos_entrada / PARCELA_MINIMA_DEMAIS)
                if num_parcelas_regular == 0:
                    num_parcelas_regular = 1
                valor_parcela_regular = _round(saldo_apos_entrada / Decimal(num_parcelas_regular))
        else:
            valor_parcela_regular = Decimal("0")
            num_parcelas_regular = 0

        parcela_num = 1
        for _ in range(entrada_parcelas):
            fluxo.append(
                {
                    "tipo": "entrada",
                    "valor": valor_parcela_entrada,
                    "parcela": parcela_num,
                }
            )
            parcela_num += 1

        for _ in range(num_parcelas_regular):
            fluxo.append(
                {
                    "tipo": "regular",
                    "valor": valor_parcela_regular,
                    "parcela": parcela_num,
                }
            )
            parcela_num += 1

    return CategoriaResult(
        nome=nome,
        componentes=componentes,
        desconto_result=desconto_result,
        prazo_total=prazo_total,
        entrada=entrada_parcelas,
        parcelas=parcelas_restantes,
        saldo=saldo,
        fluxo=fluxo,
    )


def _determinar_desconto_percentual(
    rating: RatingCAPAG,
    is_me_epp: bool,
    desconto_escolha: str,
) -> Decimal:
    """Determina o percentual de desconto com base no rating, regime e escolha.

    Para ratings A e B, o desconto é sempre 0.
    Para ratings C e D:
    - "MAIOR": desconto máximo (70% ME/EPP, 65% geral).
    - "MENOR": metade do máximo (35% ME/EPP, 32.5% geral).

    Args:
        rating: RatingCAPAG calculado.
        is_me_epp: True se contribuinte é ME/EPP/PF.
        desconto_escolha: "MAIOR" ou "MENOR".

    Returns:
        Decimal com percentual de desconto.

    References:
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
        - Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF).
    """
    if rating in (RatingCAPAG.A, RatingCAPAG.B):
        return Decimal("0")

    desconto_maximo = DESCONTO_MAX_ME_EPP if is_me_epp else DESCONTO_MAX_GERAL

    if desconto_escolha == "MAIOR":
        return desconto_maximo

    # "MENOR": metade do máximo (sem arredondar percentual para preservar precisão)
    return desconto_maximo / Decimal("2")


def calcular_simulacao_avancada(inp: SimulacaoAvancadaInput) -> SimulacaoAvancadaResult:
    """Calcula a simulação avançada completa de transação tributária.

    Executa todos os passos do cálculo (rating CAPAG, desconto por componente,
    categorias, honorários) e registra cada passo em ``calculo_detalhes``
    com fórmula e referência legal para total transparência.

    Args:
        inp: Dados de entrada (SimulacaoAvancadaInput frozen dataclass).

    Returns:
        SimulacaoAvancadaResult com todos os valores calculados e detalhes.

    References:
        - Portaria PGFN 6.757/2022, art. 24 (classificação CAPAG).
        - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal).
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
        - Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF).
        - CF/88, art. 195, §11 (limite previdenciário).
    """
    detalhes: list[dict] = []
    passo = 1

    # --- Passo 1: Calcular passivo total ---
    passivo_total = _round(inp.passivo_rfb + inp.passivo_pgfn)

    detalhes.append(
        {
            "passo": passo,
            "descricao": "Passivo total consolidado (RFB + PGFN)",
            "formula": (
                f"R$ {inp.passivo_rfb:,.2f} (RFB) + R$ {inp.passivo_pgfn:,.2f} (PGFN) " f"= R$ {passivo_total:,.2f}"
            ),
            "referencia_legal": "Portaria PGFN 6.757/2022, art. 21 (consolidação de passivos)",
        }
    )
    passo += 1

    # --- Passo 2: Rating CAPAG ---
    rating = calcular_rating_capag(inp.capag_60m, passivo_total)

    if passivo_total > Decimal("0"):
        ratio = inp.capag_60m / passivo_total
        ratio_display = f"{ratio:.4f}"
    else:
        ratio_display = "N/A (sem dívida)"

    detalhes.append(
        {
            "passo": passo,
            "descricao": f"Rating CAPAG: {rating.value} (ratio = {ratio_display})",
            "formula": (
                f"CAPAG R$ {inp.capag_60m:,.2f} / Passivo R$ {passivo_total:,.2f} "
                f"= {ratio_display} → Rating {rating.value}"
            ),
            "referencia_legal": "Portaria PGFN 6.757/2022, art. 24 (classificação por capacidade de pagamento)",
        }
    )
    passo += 1

    # --- Passo 3: Determinar percentual de desconto ---
    desconto_pct = _determinar_desconto_percentual(rating, inp.is_me_epp, inp.desconto_escolha)

    regime = "ME/EPP/PF" if inp.is_me_epp else "demais contribuintes"
    pct_display = f"{desconto_pct * 100:.1f}".rstrip("0").rstrip(".")

    if rating in (RatingCAPAG.A, RatingCAPAG.B):
        ref_desconto = "Portaria PGFN 6.757/2022, arts. 21-25 (sem desconto para rating A/B)"
    elif inp.is_me_epp:
        ref_desconto = "Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF)"
    else:
        ref_desconto = "Lei 13.988/2020, art. 11, §2º, II (limite 65% geral)"

    metodo_label = (
        "Método CAPAG (saldo transacionado = capacidade de pagamento)"
        if inp.metodo_desconto == "CAPAG"
        else "Método PERCENTUAL (% fixo sobre multa/juros/encargos)"
    )

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Desconto de {pct_display}% ({regime}, rating {rating.value}, "
                f"escolha {inp.desconto_escolha}) — {metodo_label}"
            ),
            "formula": (
                f"Rating {rating.value} + {regime} + escolha {inp.desconto_escolha} "
                f"→ {pct_display}% (método: {inp.metodo_desconto})"
            ),
            "referencia_legal": (
                f"{ref_desconto}; " f"Portaria PGFN 6.757/2022, art. 24 (princípio: saldo = CAPAG)"
                if inp.metodo_desconto == "CAPAG"
                else ref_desconto
            ),
        }
    )
    passo += 1

    # --- Passo 4: Desconto por categoria — Previdenciário ---
    cat_prev = _calcular_categoria(
        nome="Previdenciário",
        componentes=inp.previdenciario,
        desconto_pct=desconto_pct,
        is_me_epp=inp.is_me_epp,
        is_previdenciario=True,
        metodo_desconto=inp.metodo_desconto,
        capag_60m=inp.capag_60m,
        passivo_pgfn=inp.passivo_pgfn,
    )

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Previdenciário: desconto sobre multa/juros/encargos (principal preservado), "
                f"prazo {cat_prev.prazo_total} meses"
            ),
            "formula": (
                f"P={inp.previdenciario.principal} (sem desc) + "
                f"M={inp.previdenciario.multa}×{pct_display}% + "
                f"J={inp.previdenciario.juros}×{pct_display}% + "
                f"E={inp.previdenciario.encargos}×{pct_display}% → "
                f"Total final R$ {cat_prev.desconto_result.total_final:,.2f}"
            ),
            "referencia_legal": (
                "Lei 13.988/2020, art. 11, §2º, I (principal sem desconto); "
                "CF/88, art. 195, §11 (limite 60 meses previdenciário)"
            ),
        }
    )
    passo += 1

    # --- Passo 5: Desconto por categoria — Tributário ---
    cat_trib = _calcular_categoria(
        nome="Tributário",
        componentes=inp.tributario,
        desconto_pct=desconto_pct,
        is_me_epp=inp.is_me_epp,
        is_previdenciario=False,
        metodo_desconto=inp.metodo_desconto,
        capag_60m=inp.capag_60m,
        passivo_pgfn=inp.passivo_pgfn,
    )

    ref_trib = (
        "Lei 13.988/2020, art. 11, §3º (145 meses ME/EPP)"
        if inp.is_me_epp
        else "Lei 13.988/2020, art. 11, §2º, III (120 meses geral)"
    )

    detalhes.append(
        {
            "passo": passo,
            "descricao": (
                f"Tributário: desconto sobre multa/juros/encargos (principal preservado), "
                f"prazo {cat_trib.prazo_total} meses"
            ),
            "formula": (
                f"P={inp.tributario.principal} (sem desc) + "
                f"M={inp.tributario.multa}×{pct_display}% + "
                f"J={inp.tributario.juros}×{pct_display}% + "
                f"E={inp.tributario.encargos}×{pct_display}% → "
                f"Total final R$ {cat_trib.desconto_result.total_final:,.2f}"
            ),
            "referencia_legal": (f"Lei 13.988/2020, art. 11, §2º, I (principal sem desconto); " f"{ref_trib}"),
        }
    )
    passo += 1

    # --- Passo 6 (opcional): Simples Nacional ---
    cat_simples: Optional[CategoriaResult] = None
    if inp.simples is not None:
        cat_simples = _calcular_categoria(
            nome="Simples Nacional",
            componentes=inp.simples,
            desconto_pct=desconto_pct,
            is_me_epp=inp.is_me_epp,
            is_previdenciario=False,
            metodo_desconto=inp.metodo_desconto,
            capag_60m=inp.capag_60m,
            passivo_pgfn=inp.passivo_pgfn,
        )

        detalhes.append(
            {
                "passo": passo,
                "descricao": (
                    f"Simples Nacional: desconto sobre multa/juros/encargos (principal preservado), "
                    f"prazo {cat_simples.prazo_total} meses"
                ),
                "formula": (
                    f"P={inp.simples.principal} (sem desc) + "
                    f"M={inp.simples.multa}×{pct_display}% + "
                    f"J={inp.simples.juros}×{pct_display}% + "
                    f"E={inp.simples.encargos}×{pct_display}% → "
                    f"Total final R$ {cat_simples.desconto_result.total_final:,.2f}"
                ),
                "referencia_legal": (
                    "Lei 13.988/2020, art. 11, §2º, I (principal sem desconto); "
                    "Lei Complementar 123/2006 (Simples Nacional)"
                ),
            }
        )
        passo += 1

    # --- Passo N: Desconto total ---
    desconto_total = _round(
        cat_prev.desconto_result.total_desconto
        + cat_trib.desconto_result.total_desconto
        + (cat_simples.desconto_result.total_desconto if cat_simples else Decimal("0"))
    )

    desconto_efetivo = min(desconto_total, inp.passivo_pgfn)

    saldo = _round(inp.passivo_pgfn - desconto_efetivo)

    detalhes.append(
        {
            "passo": passo,
            "descricao": "Desconto total e saldo PGFN",
            "formula": (
                f"Desconto total: R$ {desconto_total:,.2f} "
                f"(limitado ao passivo PGFN R$ {inp.passivo_pgfn:,.2f}) → "
                f"Desconto efetivo: R$ {desconto_efetivo:,.2f}; "
                f"Saldo: R$ {inp.passivo_pgfn:,.2f} - R$ {desconto_efetivo:,.2f} "
                f"= R$ {saldo:,.2f}"
            ),
            "referencia_legal": "Lei 13.988/2020, art. 11 (desconto sobre crédito inscrito em dívida ativa)",
        }
    )
    passo += 1

    # --- Passo N+1: Honorários ---
    honorarios = _round(desconto_efetivo * inp.honorarios_percentual)

    pct_hon_display = f"{inp.honorarios_percentual * 100:.0f}"

    detalhes.append(
        {
            "passo": passo,
            "descricao": f"Honorários ({pct_hon_display}% sobre desconto efetivo)",
            "formula": (f"R$ {desconto_efetivo:,.2f} × {pct_hon_display}% = R$ {honorarios:,.2f}"),
            "referencia_legal": "Contrato de honorários advocatícios (percentual sobre economia obtida)",
        }
    )

    # --- Montar passivos ---
    passivos = {
        "rfb": inp.passivo_rfb,
        "pgfn": inp.passivo_pgfn,
        "total": passivo_total,
        "saldo": saldo,
    }

    return SimulacaoAvancadaResult(
        rating=rating,
        desconto_percentual=desconto_pct,
        desconto_total=desconto_total,
        desconto_efetivo=desconto_efetivo,
        previdenciario=cat_prev,
        tributario=cat_trib,
        simples=cat_simples,
        passivos=passivos,
        honorarios=honorarios,
        calculo_detalhes=detalhes,
    )
