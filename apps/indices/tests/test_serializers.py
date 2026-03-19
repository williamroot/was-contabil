"""Testes dos serializers de indices economicos.

Valida serializacao de IndiceSerializer e SelicAcumuladaResponseSerializer.
"""

from datetime import date
from decimal import Decimal

from apps.indices.serializers import IndiceSerializer, SelicAcumuladaResponseSerializer


class TestIndiceSerializer:
    """Testa IndiceSerializer."""

    def test_serializa_indice(self):
        """Serializa corretamente um objeto com data_referencia e valor."""

        class FakeIndice:
            data_referencia = date(2026, 1, 1)
            valor = Decimal("0.870000")

        s = IndiceSerializer(FakeIndice())
        data = s.data
        assert data["data"] == "2026-01-01"
        assert Decimal(data["valor"]) == Decimal("0.870000")

    def test_campo_data_mapeado_de_data_referencia(self):
        """O campo 'data' eh mapeado via source='data_referencia'."""

        class FakeIndice:
            data_referencia = date(2026, 6, 15)
            valor = Decimal("1.23")

        s = IndiceSerializer(FakeIndice())
        assert "data" in s.data


class TestSelicAcumuladaResponseSerializer:
    """Testa SelicAcumuladaResponseSerializer."""

    def test_serializa_resposta(self):
        """Serializa resposta com data_inicial, data_final e fator_acumulado."""
        data = {
            "data_inicial": date(2026, 1, 1),
            "data_final": date(2026, 6, 30),
            "fator_acumulado": Decimal("1.0540000000"),
        }
        s = SelicAcumuladaResponseSerializer(data)
        result = s.data
        assert result["data_inicial"] == "2026-01-01"
        assert result["data_final"] == "2026-06-30"
        assert Decimal(result["fator_acumulado"]) == Decimal("1.0540000000")
