"""Utilitário compartilhado para arredondamento Decimal.

Centraliza a lógica de arredondamento financeiro (2 casas, ROUND_HALF_UP)
usada em todos os engines de cálculo do projeto.
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def round_decimal(value: Decimal) -> Decimal:
    """Arredonda Decimal para 2 casas com ROUND_HALF_UP.

    Padrão bancário brasileiro para valores monetários.

    Args:
        value: Valor Decimal a ser arredondado.

    Returns:
        Decimal arredondado para centavos.
    """
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
