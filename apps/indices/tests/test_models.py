"""Testes do model IndiceEconomico.

Valida __str__, unique_together e ordering.
"""

from datetime import date
from decimal import Decimal

import pytest

from django.db import IntegrityError

from apps.indices.models import IndiceEconomico


@pytest.mark.django_db
class TestIndiceEconomicoModel:
    """Testa model IndiceEconomico."""

    def test_str_representation(self):
        """__str__ retorna 'serie_nome data_referencia = valor'."""
        indice = IndiceEconomico.objects.create(
            serie_codigo=4390,
            serie_nome="SELIC mensal",
            data_referencia=date(2026, 1, 1),
            valor=Decimal("0.870000"),
        )
        assert str(indice) == "SELIC mensal 2026-01-01 = 0.870000"

    def test_unique_together_serie_data(self):
        """Nao deve permitir duplicata de (serie_codigo, data_referencia)."""
        IndiceEconomico.objects.create(
            serie_codigo=4390,
            serie_nome="SELIC mensal",
            data_referencia=date(2026, 1, 1),
            valor=Decimal("0.870000"),
        )
        with pytest.raises(IntegrityError):
            IndiceEconomico.objects.create(
                serie_codigo=4390,
                serie_nome="SELIC mensal",
                data_referencia=date(2026, 1, 1),
                valor=Decimal("0.900000"),
            )

    def test_ordering_por_serie_e_data(self):
        """Indices sao ordenados por serie_codigo e data_referencia."""
        IndiceEconomico.objects.create(
            serie_codigo=4390,
            serie_nome="SELIC mensal",
            data_referencia=date(2026, 2, 1),
            valor=Decimal("0.820000"),
        )
        IndiceEconomico.objects.create(
            serie_codigo=4390,
            serie_nome="SELIC mensal",
            data_referencia=date(2026, 1, 1),
            valor=Decimal("0.870000"),
        )
        IndiceEconomico.objects.create(
            serie_codigo=433,
            serie_nome="IPCA mensal",
            data_referencia=date(2026, 1, 1),
            valor=Decimal("0.500000"),
        )

        indices = list(IndiceEconomico.objects.all())
        # 433 vem antes de 4390, e dentro de cada serie por data
        assert indices[0].serie_codigo == 433
        assert indices[1].serie_codigo == 4390
        assert indices[1].data_referencia == date(2026, 1, 1)
        assert indices[2].data_referencia == date(2026, 2, 1)

    def test_created_at_auto(self):
        """created_at eh preenchido automaticamente."""
        indice = IndiceEconomico.objects.create(
            serie_codigo=4390,
            serie_nome="SELIC mensal",
            data_referencia=date(2026, 3, 1),
            valor=Decimal("0.750000"),
        )
        assert indice.created_at is not None
