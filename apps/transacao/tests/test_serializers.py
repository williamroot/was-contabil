"""Testes dos serializers de transacao tributaria (basica e avancada).

Valida entradas do request: classificacao, desconto_escolha,
componentes P/M/J/E, limites decimais e campos obrigatorios.
"""

from apps.transacao.serializers import (
    DebitoComponentesSerializer,
    SimulacaoAvancadaRequestSerializer,
    SimulacaoBasicaRequestSerializer,
)

# ---------------------------------------------------------------------------
# SimulacaoBasicaRequestSerializer
# ---------------------------------------------------------------------------


class TestSimulacaoBasicaRequestSerializer:
    """Testa validacao do serializer de simulacao basica."""

    def _valid_payload(self, **overrides):
        payload = {
            "valor_total_divida": "100000.00",
            "percentual_previdenciario": "0.3000",
            "is_me_epp": False,
            "classificacao": "D",
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo e valido eh aceito."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_classificacao_a_valida(self):
        """Classificacao A eh aceita."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="A"))
        assert s.is_valid(), s.errors
        assert s.validated_data["classificacao"] == "A"

    def test_classificacao_b_valida(self):
        """Classificacao B eh aceita."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="B"))
        assert s.is_valid(), s.errors

    def test_classificacao_c_valida(self):
        """Classificacao C eh aceita."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="C"))
        assert s.is_valid(), s.errors

    def test_classificacao_d_valida(self):
        """Classificacao D eh aceita."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="D"))
        assert s.is_valid(), s.errors

    def test_classificacao_minuscula_normalizada(self):
        """Classificacao minuscula eh normalizada para maiuscula."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="d"))
        assert s.is_valid(), s.errors
        assert s.validated_data["classificacao"] == "D"

    def test_classificacao_invalida_rejeita(self):
        """Classificacao E nao existe, deve rejeitar."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="E"))
        assert not s.is_valid()
        assert "classificacao" in s.errors

    def test_classificacao_invalida_z_rejeita(self):
        """Classificacao Z nao existe, deve rejeitar."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(classificacao="Z"))
        assert not s.is_valid()
        assert "classificacao" in s.errors

    def test_valor_total_divida_minimo_1(self):
        """Valor total da divida minimo eh R$ 1,00."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(valor_total_divida="1.00"))
        assert s.is_valid(), s.errors

    def test_valor_total_divida_zero_rejeita(self):
        """Valor total zero deve ser rejeitado (min_value=1)."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(valor_total_divida="0.00"))
        assert not s.is_valid()
        assert "valor_total_divida" in s.errors

    def test_valor_total_divida_negativo_rejeita(self):
        """Valor total negativo deve ser rejeitado."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(valor_total_divida="-100.00"))
        assert not s.is_valid()
        assert "valor_total_divida" in s.errors

    def test_percentual_previdenciario_zero_valido(self):
        """Percentual previdenciario 0 (100% tributario) eh valido."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(percentual_previdenciario="0.0000"))
        assert s.is_valid(), s.errors

    def test_percentual_previdenciario_1_valido(self):
        """Percentual previdenciario 1 (100% previdenciario) eh valido."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(percentual_previdenciario="1.0000"))
        assert s.is_valid(), s.errors

    def test_percentual_previdenciario_acima_1_rejeita(self):
        """Percentual > 1 eh impossivel, deve rejeitar."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(percentual_previdenciario="1.0001"))
        assert not s.is_valid()
        assert "percentual_previdenciario" in s.errors

    def test_percentual_previdenciario_negativo_rejeita(self):
        """Percentual negativo deve rejeitar."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(percentual_previdenciario="-0.1000"))
        assert not s.is_valid()
        assert "percentual_previdenciario" in s.errors

    def test_is_me_epp_default_false(self):
        """is_me_epp tem default False."""
        payload = self._valid_payload()
        del payload["is_me_epp"]
        s = SimulacaoBasicaRequestSerializer(data=payload)
        assert s.is_valid(), s.errors
        assert s.validated_data["is_me_epp"] is False

    def test_classificacao_default_d(self):
        """classificacao tem default D."""
        payload = self._valid_payload()
        del payload["classificacao"]
        s = SimulacaoBasicaRequestSerializer(data=payload)
        assert s.is_valid(), s.errors
        assert s.validated_data["classificacao"] == "D"

    def test_decimal_precision_15_digitos(self):
        """Aceita valor com ate 15 digitos e 2 casas decimais."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(valor_total_divida="9999999999999.99"))
        assert s.is_valid(), s.errors

    def test_valor_muito_grande_rejeita(self):
        """Valor excedendo max_digits=15 deve rejeitar."""
        s = SimulacaoBasicaRequestSerializer(data=self._valid_payload(valor_total_divida="99999999999999.99"))
        assert not s.is_valid()
        assert "valor_total_divida" in s.errors


# ---------------------------------------------------------------------------
# SimulacaoAvancadaRequestSerializer
# ---------------------------------------------------------------------------


class TestSimulacaoAvancadaRequestSerializer:
    """Testa validacao do serializer de simulacao avancada."""

    def _valid_payload(self, **overrides):
        payload = {
            "passivo_rfb": "5000.00",
            "passivo_pgfn": "4800.00",
            "capag_60m": "1000.00",
            "is_me_epp": True,
            "desconto_escolha": "MAIOR",
            "honorarios_percentual": "0.20",
            "previdenciario": {
                "principal": "1000.00",
                "multa": "300.00",
                "juros": "500.00",
                "encargos": "200.00",
            },
            "tributario": {
                "principal": "1500.00",
                "multa": "450.00",
                "juros": "600.00",
                "encargos": "250.00",
            },
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo e valido eh aceito."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_desconto_escolha_maior_valido(self):
        """desconto_escolha MAIOR eh aceito."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(desconto_escolha="MAIOR"))
        assert s.is_valid(), s.errors

    def test_desconto_escolha_menor_valido(self):
        """desconto_escolha MENOR eh aceito."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(desconto_escolha="MENOR"))
        assert s.is_valid(), s.errors

    def test_desconto_escolha_minuscula_normalizada(self):
        """desconto_escolha minuscula normalizada para maiuscula."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(desconto_escolha="maior"))
        assert s.is_valid(), s.errors
        assert s.validated_data["desconto_escolha"] == "MAIOR"

    def test_desconto_escolha_invalido_rejeita(self):
        """desconto_escolha com valor invalido deve rejeitar."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(desconto_escolha="MEDIO"))
        assert not s.is_valid()
        assert "desconto_escolha" in s.errors

    def test_passivo_rfb_negativo_rejeita(self):
        """Passivo RFB negativo deve rejeitar."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(passivo_rfb="-100.00"))
        assert not s.is_valid()
        assert "passivo_rfb" in s.errors

    def test_honorarios_acima_1_rejeita(self):
        """Honorarios acima de 100% (1.0) deve rejeitar."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(honorarios_percentual="1.01"))
        assert not s.is_valid()
        assert "honorarios_percentual" in s.errors

    def test_honorarios_zero_valido(self):
        """Honorarios zero (sem honorarios) eh valido."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload(honorarios_percentual="0.00"))
        assert s.is_valid(), s.errors

    def test_simples_opcional(self):
        """Campo simples eh opcional, payload sem simples eh valido."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_simples_preenchido_valido(self):
        """Campo simples preenchido com P/M/J/E eh valido."""
        payload = self._valid_payload()
        payload["simples"] = {
            "principal": "800.00",
            "multa": "200.00",
            "juros": "300.00",
            "encargos": "100.00",
        }
        s = SimulacaoAvancadaRequestSerializer(data=payload)
        assert s.is_valid(), s.errors

    def test_componentes_negativos_rejeita(self):
        """Componentes negativos em previdenciario devem rejeitar."""
        payload = self._valid_payload()
        payload["previdenciario"]["principal"] = "-100.00"
        s = SimulacaoAvancadaRequestSerializer(data=payload)
        assert not s.is_valid()

    def test_empresa_id_opcional(self):
        """empresa_id eh opcional."""
        s = SimulacaoAvancadaRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors
        assert s.validated_data.get("empresa_id") is None


# ---------------------------------------------------------------------------
# DebitoComponentesSerializer
# ---------------------------------------------------------------------------


class TestDebitoComponentesSerializer:
    """Testa validacao do serializer de componentes P/M/J/E."""

    def test_componentes_validos(self):
        """Componentes validos sao aceitos."""
        data = {
            "principal": "1000.00",
            "multa": "300.00",
            "juros": "500.00",
            "encargos": "200.00",
        }
        s = DebitoComponentesSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_componente_negativo_rejeita(self):
        """Valor negativo em qualquer componente deve rejeitar."""
        data = {
            "principal": "-1.00",
            "multa": "300.00",
            "juros": "500.00",
            "encargos": "200.00",
        }
        s = DebitoComponentesSerializer(data=data)
        assert not s.is_valid()
        assert "principal" in s.errors

    def test_todos_zeros_valido(self):
        """Componentes todos zero sao aceitos (min_value=0)."""
        data = {
            "principal": "0.00",
            "multa": "0.00",
            "juros": "0.00",
            "encargos": "0.00",
        }
        s = DebitoComponentesSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_campo_faltando_rejeita(self):
        """Campo obrigatorio faltando deve rejeitar."""
        data = {
            "principal": "1000.00",
            "multa": "300.00",
        }
        s = DebitoComponentesSerializer(data=data)
        assert not s.is_valid()
        assert "juros" in s.errors
        assert "encargos" in s.errors
