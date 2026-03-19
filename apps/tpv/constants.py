"""Constantes legais do módulo TPV — Transação de Pequeno Valor.

Referência legal: Edital PGDAU 11/2025 (vigente até 29/05/2026).
Todas as constantes monetárias usam Decimal para precisão financeira.
"""

from decimal import Decimal
from typing import Optional

# --- Entrada ---
# Edital PGDAU 11/2025: entrada de 5% em até 5 parcelas
ENTRADA_PERCENTUAL_TPV: Decimal = Decimal("0.05")
ENTRADA_PARCELAS_MAX_TPV: int = 5

# --- Elegibilidade por CDA ---
# Edital PGDAU 11/2025: CDA elegível até 60 salários mínimos
LIMITE_SM_POR_CDA: int = 60

# Edital PGDAU 11/2025: CDA deve estar inscrita há mais de 1 ano (365 dias)
TEMPO_MINIMO_INSCRICAO_DIAS: int = 365

# --- Salário mínimo vigente ---
# Decreto 12.342/2025: R$ 1.621,00 a partir de 01/01/2026
SALARIO_MINIMO_2026: Decimal = Decimal("1621")

# --- Tabela de descontos escalonados ---
# Edital PGDAU 11/2025: desconto incide sobre TODO o saldo
# (inclusive principal — exceção legal TPV, art. 11, §2º, I da Lei 13.988)
TABELA_DESCONTOS_TPV: list[dict] = [
    {"desconto": Decimal("0.50"), "parcelas": 7},
    {"desconto": Decimal("0.45"), "parcelas": 12},
    {"desconto": Decimal("0.40"), "parcelas": 30},
    {"desconto": Decimal("0.30"), "parcelas": 55},
]

# Mapeamento inverso: parcelas -> desconto (para lookup rápido)
_PARCELAS_PARA_DESCONTO: dict[int, Decimal] = {faixa["parcelas"]: faixa["desconto"] for faixa in TABELA_DESCONTOS_TPV}

# Tipos de contribuinte elegíveis para TPV
TIPOS_CONTRIBUINTE_ELEGIVEIS: tuple[str, ...] = ("PF", "ME", "EPP")


def get_desconto_por_parcelas(parcelas: int) -> Decimal:
    """Retorna o percentual de desconto para o número de parcelas informado.

    Referência: Edital PGDAU 11/2025 — tabela de descontos escalonados.

    Args:
        parcelas: Número de parcelas do saldo (7, 12, 30 ou 55).

    Returns:
        Percentual de desconto como Decimal (ex: Decimal("0.50") para 50%).

    Raises:
        ValueError: Se o número de parcelas não corresponde a nenhuma faixa.
    """
    desconto = _PARCELAS_PARA_DESCONTO.get(parcelas)
    if desconto is None:
        faixas_validas = sorted(_PARCELAS_PARA_DESCONTO.keys())
        raise ValueError(f"Número de parcelas inválido: {parcelas}. " f"Faixas válidas: {faixas_validas}")
    return desconto


def calcular_limite_valor_cda(salario_minimo: Optional[Decimal] = None) -> Decimal:
    """Calcula o limite máximo de valor por CDA para elegibilidade TPV.

    Fórmula: LIMITE_SM_POR_CDA × salário mínimo vigente.

    Referência: Edital PGDAU 11/2025 — CDA elegível até 60 SM.

    Args:
        salario_minimo: Valor do salário mínimo. Se None, usa SALARIO_MINIMO_2026.

    Returns:
        Limite máximo em Decimal (ex: Decimal("97260") para SM R$ 1.621,00).
    """
    if salario_minimo is None:
        salario_minimo = SALARIO_MINIMO_2026
    return Decimal(LIMITE_SM_POR_CDA) * salario_minimo
