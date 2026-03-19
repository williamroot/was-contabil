"""Template filters para PDFs do WAS Contabil.

Filtros customizados para formatacao de valores nos templates PDF.
"""

from django import template

register = template.Library()


@register.filter
def as_percent(value):
    """Converte decimal (0.65) para percentual (65.0).

    Exemplo: {{ desconto_percentual|as_percent|floatformat:1 }}%
    Entrada 0.65 -> Saida 65.0
    """
    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return value
