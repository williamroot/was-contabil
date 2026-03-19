"""Testes do serializer de comparacao CAPAG vs TPV.

Valida classificacao, campos obrigatorios e limites decimais.
"""

from apps.comparador.serializers import ComparacaoRequestSerializer


class TestComparacaoRequestSerializer:
    """Testa validacao do ComparacaoRequestSerializer."""

    def _valid_payload(self, **overrides):
        payload = {
            "valor_total": "100000.00",
            "percentual_previdenciario": "0.3000",
            "is_me_epp": True,
            "classificacao": "D",
            "tpv_elegivel": True,
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo valido eh aceito."""
        s = ComparacaoRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_classificacao_a_valida(self):
        """Classificacao A eh aceita."""
        s = ComparacaoRequestSerializer(data=self._valid_payload(classificacao="A"))
        assert s.is_valid(), s.errors

    def test_classificacao_invalida_rejeita(self):
        """Classificacao invalida E deve rejeitar."""
        s = ComparacaoRequestSerializer(data=self._valid_payload(classificacao="E"))
        assert not s.is_valid()
        assert "classificacao" in s.errors

    def test_classificacao_minuscula_normalizada(self):
        """Classificacao minuscula normalizada para maiuscula."""
        s = ComparacaoRequestSerializer(data=self._valid_payload(classificacao="c"))
        assert s.is_valid(), s.errors
        assert s.validated_data["classificacao"] == "C"

    def test_valor_total_minimo_1(self):
        """Valor total minimo eh 1."""
        s = ComparacaoRequestSerializer(data=self._valid_payload(valor_total="0.50"))
        assert not s.is_valid()
        assert "valor_total" in s.errors

    def test_percentual_previdenciario_acima_1_rejeita(self):
        """Percentual > 1 deve rejeitar."""
        s = ComparacaoRequestSerializer(data=self._valid_payload(percentual_previdenciario="1.0001"))
        assert not s.is_valid()
        assert "percentual_previdenciario" in s.errors

    def test_tpv_elegivel_default_false(self):
        """tpv_elegivel tem default False."""
        payload = self._valid_payload()
        del payload["tpv_elegivel"]
        s = ComparacaoRequestSerializer(data=payload)
        assert s.is_valid(), s.errors
        assert s.validated_data["tpv_elegivel"] is False
