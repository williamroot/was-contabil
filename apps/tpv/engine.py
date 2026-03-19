"""Engine de calculo TPV — Transacao de Pequeno Valor.

Referencia legal: Edital PGDAU 11/2025 (vigente ate 29/05/2026).
Lei 13.988/2020, art. 11, par. 2, I — desconto sobre todo o saldo (inclusive principal).

Modulo Python puro — sem Django, sem I/O.
Usa Decimal com ROUND_HALF_UP para precisao financeira.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.core.decimal_utils import round_decimal as _round
from apps.tpv.constants import (
    ENTRADA_PARCELAS_MAX_TPV,
    ENTRADA_PERCENTUAL_TPV,
    TABELA_DESCONTOS_TPV,
    get_desconto_por_parcelas,
)
from apps.tpv.validators import CDAValidationResult, validar_cda

# ---------------------------------------------------------------------------
# Dataclasses de entrada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CDAInput:
    """Dados de entrada de uma CDA para simulacao TPV.

    Attributes:
        numero: Numero identificador da CDA.
        valor: Valor consolidado da CDA em Decimal.
        data_inscricao: Data de inscricao da CDA em divida ativa.
    """

    numero: str
    valor: Decimal
    data_inscricao: date


@dataclass
class CDAResult:
    """Resultado da validacao de uma CDA individual.

    Attributes:
        numero: Numero identificador da CDA.
        valor: Valor consolidado da CDA.
        data_inscricao: Data de inscricao.
        validacao: Resultado da validacao de elegibilidade.
    """

    numero: str
    valor: Decimal
    data_inscricao: date
    validacao: CDAValidationResult


@dataclass
class TPVInput:
    """Dados de entrada para simulacao TPV.

    Attributes:
        cdas: Lista de CDAs para simulacao.
        parcelas_entrada: Numero de parcelas da entrada (1 a 5).
        parcelas_saldo: Numero de parcelas do saldo (7, 12, 30 ou 55).
        salario_minimo: Valor do salario minimo vigente.
        data_simulacao: Data da simulacao (referencia para elegibilidade).
    """

    cdas: list[CDAInput]
    parcelas_entrada: int
    parcelas_saldo: int
    salario_minimo: Decimal
    data_simulacao: date


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------


@dataclass
class TPVResult:
    """Resultado de simulacao TPV para um conjunto de CDAs.

    Referencia: Edital PGDAU 11/2025.

    Attributes:
        total_cdas_aptas: Soma dos valores das CDAs aptas.
        cdas_aptas: Lista de CDAResult aptas.
        cdas_nao_aptas: Lista de CDAResult nao aptas.
        entrada: Valor total da entrada (5% do total aptas).
        desconto: Percentual de desconto aplicado (Decimal, ex: 0.50).
        saldo: Valor do saldo apos desconto.
        parcelas: Lista de valores das parcelas do saldo.
        valor_final: Valor final pago (entrada + saldo).
        economia: Economia obtida (total_cdas_aptas - valor_final).
        fluxo: Lista de dicts com tipo ('entrada'/'saldo'), numero e valor.
    """

    total_cdas_aptas: Decimal
    cdas_aptas: list[CDAResult]
    cdas_nao_aptas: list[CDAResult]
    entrada: Decimal
    desconto: Decimal
    saldo: Decimal
    parcelas: list[Decimal]
    valor_final: Decimal
    economia: Decimal
    fluxo: list[dict] = field(default_factory=list)


@dataclass
class FaixaResult:
    """Resultado de uma faixa de desconto na simulacao multi-faixa.

    Referencia: Edital PGDAU 11/2025 — tabela de descontos escalonados.

    Attributes:
        desconto_percentual: Percentual de desconto (ex: Decimal("0.50")).
        parcelas_max: Numero maximo de parcelas da faixa.
        desconto_valor: Valor absoluto do desconto.
        saldo_final: Saldo apos desconto.
        parcela_saldo: Valor de cada parcela do saldo.
        valor_final: Valor final pago (entrada + saldo_final).
        is_melhor: True se esta e a melhor faixa (maior economia).
    """

    desconto_percentual: Decimal
    parcelas_max: int
    desconto_valor: Decimal
    saldo_final: Decimal
    parcela_saldo: Decimal
    valor_final: Decimal
    is_melhor: bool = False


@dataclass
class TPVMultiFaixaResult:
    """Resultado da simulacao TPV com todas as faixas de desconto.

    Referencia: Edital PGDAU 11/2025.

    Attributes:
        valor_original: Valor total original das CDAs.
        valor_entrada: Valor total da entrada (5%).
        parcela_entrada: Valor de cada parcela da entrada.
        saldo_apos_entrada: Saldo apos abater a entrada.
        faixas: Lista de FaixaResult para cada faixa de desconto.
        melhor_faixa: Referencia a faixa com maior economia.
        economia_maxima: Valor da maior economia (desconto da melhor faixa).
    """

    valor_original: Decimal
    valor_entrada: Decimal
    parcela_entrada: Decimal
    saldo_apos_entrada: Decimal
    faixas: list[FaixaResult]
    melhor_faixa: FaixaResult
    economia_maxima: Decimal


# ---------------------------------------------------------------------------
# Funcoes de calculo
# ---------------------------------------------------------------------------


def _validar_cdas(
    cdas: list[CDAInput],
    salario_minimo: Decimal,
    data_simulacao: date,
) -> tuple[list[CDAResult], list[CDAResult]]:
    """Valida lista de CDAs e separa em aptas e nao aptas.

    Args:
        cdas: Lista de CDAInput.
        salario_minimo: Salario minimo vigente.
        data_simulacao: Data da simulacao.

    Returns:
        Tupla (cdas_aptas, cdas_nao_aptas) com CDAResult.
    """
    aptas: list[CDAResult] = []
    nao_aptas: list[CDAResult] = []

    for cda in cdas:
        validacao = validar_cda(
            valor=cda.valor,
            data_inscricao=cda.data_inscricao,
            data_simulacao=data_simulacao,
            salario_minimo=salario_minimo,
        )
        resultado = CDAResult(
            numero=cda.numero,
            valor=cda.valor,
            data_inscricao=cda.data_inscricao,
            validacao=validacao,
        )
        if validacao.apta:
            aptas.append(resultado)
        else:
            nao_aptas.append(resultado)

    return aptas, nao_aptas


def _construir_fluxo(
    parcelas_entrada: int,
    valor_parcela_entrada: Decimal,
    parcelas_saldo: int,
    valor_parcela_saldo: Decimal,
) -> list[dict]:
    """Constroi o fluxo de pagamento (entrada + saldo).

    Args:
        parcelas_entrada: Numero de parcelas da entrada.
        valor_parcela_entrada: Valor de cada parcela de entrada.
        parcelas_saldo: Numero de parcelas do saldo.
        valor_parcela_saldo: Valor de cada parcela do saldo.

    Returns:
        Lista de dicts com tipo, numero e valor de cada parcela.
    """
    fluxo: list[dict] = []

    for i in range(1, parcelas_entrada + 1):
        fluxo.append(
            {
                "tipo": "entrada",
                "numero": i,
                "valor": valor_parcela_entrada,
            }
        )

    for i in range(1, parcelas_saldo + 1):
        fluxo.append(
            {
                "tipo": "saldo",
                "numero": i,
                "valor": valor_parcela_saldo,
            }
        )

    return fluxo


def calcular_tpv(inp: TPVInput) -> TPVResult:
    """Calcula simulacao TPV para um conjunto de CDAs.

    Fluxo:
    1. Valida cada CDA (elegibilidade por valor e tempo).
    2. Soma apenas CDAs aptas.
    3. Calcula entrada (5% do total).
    4. Aplica desconto sobre saldo apos entrada.
    5. Calcula parcelas e fluxo de pagamento.

    Referencia legal:
    - Edital PGDAU 11/2025 — Transacao de Pequeno Valor.
    - Lei 13.988/2020, art. 11, par. 2, I.

    Args:
        inp: TPVInput com CDAs, parcelas e parametros.

    Returns:
        TPVResult com valores calculados.
    """
    # 1. Validar CDAs
    cdas_aptas, cdas_nao_aptas = _validar_cdas(
        cdas=inp.cdas,
        salario_minimo=inp.salario_minimo,
        data_simulacao=inp.data_simulacao,
    )

    # 2. Somar valores das CDAs aptas
    total_aptas = sum((cda.valor for cda in cdas_aptas), Decimal("0"))

    # 3. Calcular entrada (5% do total)
    entrada = _round(total_aptas * ENTRADA_PERCENTUAL_TPV)
    parcela_entrada = _round(entrada / inp.parcelas_entrada)

    # 4. Saldo apos entrada
    saldo_apos_entrada = total_aptas - entrada

    # 5. Aplicar desconto sobre saldo
    desconto_percentual = get_desconto_por_parcelas(inp.parcelas_saldo)
    saldo_final = _round(saldo_apos_entrada * (Decimal("1") - desconto_percentual))

    # 6. Calcular parcelas do saldo
    parcela_saldo = _round(saldo_final / inp.parcelas_saldo)
    parcelas = [parcela_saldo] * inp.parcelas_saldo

    # 7. Valor final e economia
    valor_final = _round(entrada + saldo_final)
    economia = _round(total_aptas - valor_final)

    # 8. Construir fluxo
    fluxo = _construir_fluxo(
        parcelas_entrada=inp.parcelas_entrada,
        valor_parcela_entrada=parcela_entrada,
        parcelas_saldo=inp.parcelas_saldo,
        valor_parcela_saldo=parcela_saldo,
    )

    return TPVResult(
        total_cdas_aptas=total_aptas,
        cdas_aptas=cdas_aptas,
        cdas_nao_aptas=cdas_nao_aptas,
        entrada=entrada,
        desconto=desconto_percentual,
        saldo=saldo_final,
        parcelas=parcelas,
        valor_final=valor_final,
        economia=economia,
        fluxo=fluxo,
    )


def calcular_tpv_todas_faixas(
    valor_total: Decimal,
    parcelas_entrada: int = ENTRADA_PARCELAS_MAX_TPV,
) -> TPVMultiFaixaResult:
    """Calcula simulacao TPV para todas as faixas de desconto.

    Retorna comparacao lado a lado das 4 faixas do Edital PGDAU 11/2025:
    - 50% em ate 7 parcelas
    - 45% em ate 12 parcelas
    - 40% em ate 30 parcelas
    - 30% em ate 55 parcelas

    A melhor faixa e a de maior desconto (maior economia para o contribuinte).

    Referencia legal:
    - Edital PGDAU 11/2025 — tabela de descontos escalonados.
    - Lei 13.988/2020, art. 11, par. 2, I.

    Args:
        valor_total: Valor total das CDAs aptas.
        parcelas_entrada: Numero de parcelas da entrada (padrao 5).

    Returns:
        TPVMultiFaixaResult com todas as faixas e melhor opcao.
    """
    # Entrada: 5% do valor total
    valor_entrada = _round(valor_total * ENTRADA_PERCENTUAL_TPV)
    parcela_entrada = _round(valor_entrada / parcelas_entrada)
    saldo_apos_entrada = valor_total - valor_entrada

    # Calcular cada faixa
    faixas: list[FaixaResult] = []
    for faixa_def in TABELA_DESCONTOS_TPV:
        desconto_pct = faixa_def["desconto"]
        parcelas_max = faixa_def["parcelas"]

        # Desconto e saldo calculados independentemente e arredondados
        desconto_valor = _round(saldo_apos_entrada * desconto_pct)
        saldo_final = _round(saldo_apos_entrada * (Decimal("1") - desconto_pct))
        parcela_saldo = _round(saldo_final / parcelas_max)
        valor_final = _round(valor_entrada + saldo_final)

        faixas.append(
            FaixaResult(
                desconto_percentual=desconto_pct,
                parcelas_max=parcelas_max,
                desconto_valor=desconto_valor,
                saldo_final=saldo_final,
                parcela_saldo=parcela_saldo,
                valor_final=valor_final,
                is_melhor=False,
            )
        )

    # Melhor faixa: maior desconto (primeira da tabela, ja ordenada)
    melhor = max(faixas, key=lambda f: f.desconto_valor)
    melhor.is_melhor = True

    economia_maxima = melhor.desconto_valor

    return TPVMultiFaixaResult(
        valor_original=valor_total,
        valor_entrada=valor_entrada,
        parcela_entrada=parcela_entrada,
        saldo_apos_entrada=saldo_apos_entrada,
        faixas=faixas,
        melhor_faixa=melhor,
        economia_maxima=economia_maxima,
    )
