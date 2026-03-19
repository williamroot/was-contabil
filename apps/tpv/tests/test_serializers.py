"""Testes dos serializers TPV — Transacao de Pequeno Valor.

Valida tipo_porte, parcelas_saldo, CDAs vazias e campos obrigatorios.
"""

from apps.tpv.serializers import (
    CDARequestSerializer,
    TPVSimulacaoRequestSerializer,
    TPVWizardRequestSerializer,
)

# ---------------------------------------------------------------------------
# TPVSimulacaoRequestSerializer
# ---------------------------------------------------------------------------


class TestTPVSimulacaoRequestSerializer:
    """Testa validacao do serializer de simulacao TPV."""

    def _valid_payload(self, **overrides):
        payload = {
            "tipo_porte": "PF",
            "salario_minimo": "1621.00",
            "parcelas_entrada": 5,
            "parcelas_saldo": 7,
            "cdas": [
                {
                    "numero": "CDA-001",
                    "valor": "50000.00",
                    "data_inscricao": "2024-01-15",
                },
            ],
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo valido eh aceito."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_tipo_porte_pf_valido(self):
        """Tipo PF eh elegivel."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="PF"))
        assert s.is_valid(), s.errors
        assert s.validated_data["tipo_porte"] == "PF"

    def test_tipo_porte_me_valido(self):
        """Tipo ME eh elegivel."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="ME"))
        assert s.is_valid(), s.errors

    def test_tipo_porte_epp_valido(self):
        """Tipo EPP eh elegivel."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="EPP"))
        assert s.is_valid(), s.errors

    def test_tipo_porte_minuscula_normalizada(self):
        """Tipo minuscula normalizado para maiuscula."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="pf"))
        assert s.is_valid(), s.errors
        assert s.validated_data["tipo_porte"] == "PF"

    def test_tipo_porte_pj_invalido(self):
        """Tipo PJ nao eh elegivel para TPV."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="PJ"))
        assert not s.is_valid()
        assert "tipo_porte" in s.errors

    def test_tipo_porte_ltda_invalido(self):
        """Tipo LTDA nao eh elegivel para TPV."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(tipo_porte="LTDA"))
        assert not s.is_valid()
        assert "tipo_porte" in s.errors

    def test_parcelas_saldo_7_valido(self):
        """7 parcelas de saldo eh valido (50% desconto)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=7))
        assert s.is_valid(), s.errors

    def test_parcelas_saldo_12_valido(self):
        """12 parcelas de saldo eh valido (45% desconto)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=12))
        assert s.is_valid(), s.errors

    def test_parcelas_saldo_30_valido(self):
        """30 parcelas de saldo eh valido (40% desconto)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=30))
        assert s.is_valid(), s.errors

    def test_parcelas_saldo_55_valido(self):
        """55 parcelas de saldo eh valido (30% desconto)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=55))
        assert s.is_valid(), s.errors

    def test_parcelas_saldo_0_rejeita(self):
        """0 parcelas de saldo nao faz parte das faixas validas."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=0))
        assert not s.is_valid()
        assert "parcelas_saldo" in s.errors

    def test_parcelas_saldo_56_rejeita(self):
        """56 parcelas nao faz parte das faixas validas."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=56))
        assert not s.is_valid()
        assert "parcelas_saldo" in s.errors

    def test_parcelas_saldo_10_rejeita(self):
        """10 parcelas nao faz parte das faixas validas (7, 12, 30, 55)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_saldo=10))
        assert not s.is_valid()
        assert "parcelas_saldo" in s.errors

    def test_cdas_vazias_rejeita(self):
        """Lista de CDAs vazia deve rejeitar."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(cdas=[]))
        assert not s.is_valid()
        assert "cdas" in s.errors

    def test_parcelas_entrada_min_1(self):
        """Parcelas de entrada minimo eh 1."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_entrada=1))
        assert s.is_valid(), s.errors

    def test_parcelas_entrada_max_5(self):
        """Parcelas de entrada maximo eh 5."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_entrada=5))
        assert s.is_valid(), s.errors

    def test_parcelas_entrada_0_rejeita(self):
        """0 parcelas de entrada deve rejeitar."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_entrada=0))
        assert not s.is_valid()
        assert "parcelas_entrada" in s.errors

    def test_parcelas_entrada_6_rejeita(self):
        """6 parcelas de entrada excede o maximo (5)."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(parcelas_entrada=6))
        assert not s.is_valid()
        assert "parcelas_entrada" in s.errors

    def test_salario_minimo_positivo(self):
        """Salario minimo deve ser >= 1."""
        s = TPVSimulacaoRequestSerializer(data=self._valid_payload(salario_minimo="0.00"))
        assert not s.is_valid()
        assert "salario_minimo" in s.errors

    def test_multiplas_cdas_valido(self):
        """Multiplas CDAs sao aceitas."""
        payload = self._valid_payload()
        payload["cdas"] = [
            {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "2024-01-15"},
            {"numero": "CDA-002", "valor": "30000.00", "data_inscricao": "2024-06-01"},
        ]
        s = TPVSimulacaoRequestSerializer(data=payload)
        assert s.is_valid(), s.errors


# ---------------------------------------------------------------------------
# CDARequestSerializer
# ---------------------------------------------------------------------------


class TestCDARequestSerializer:
    """Testa validacao do serializer de CDA individual."""

    def test_cda_valida(self):
        """CDA com todos os campos validos eh aceita."""
        data = {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "2024-01-15"}
        s = CDARequestSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_cda_valor_negativo_rejeita(self):
        """Valor negativo de CDA deve rejeitar."""
        data = {"numero": "CDA-001", "valor": "-100.00", "data_inscricao": "2024-01-15"}
        s = CDARequestSerializer(data=data)
        assert not s.is_valid()
        assert "valor" in s.errors

    def test_cda_data_formato_invalido_rejeita(self):
        """Data em formato invalido deve rejeitar."""
        data = {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "15/01/2024"}
        s = CDARequestSerializer(data=data)
        assert not s.is_valid()
        assert "data_inscricao" in s.errors


# ---------------------------------------------------------------------------
# TPVWizardRequestSerializer
# ---------------------------------------------------------------------------


class TestTPVWizardRequestSerializer:
    """Testa validacao do serializer do wizard TPV."""

    def _valid_payload(self, **overrides):
        payload = {
            "tipo_contribuinte": "PF",
            "possui_cda_acima_limite": False,
            "valor_total": "50000.00",
            "todas_cdas_mais_1_ano": True,
            "salario_minimo": "1621.00",
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo valido eh aceito."""
        s = TPVWizardRequestSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_salario_minimo_obrigatorio(self):
        """Salario minimo eh obrigatorio."""
        payload = self._valid_payload()
        del payload["salario_minimo"]
        s = TPVWizardRequestSerializer(data=payload)
        assert not s.is_valid()
        assert "salario_minimo" in s.errors

    def test_valor_total_negativo_rejeita(self):
        """Valor total negativo deve rejeitar."""
        s = TPVWizardRequestSerializer(data=self._valid_payload(valor_total="-1.00"))
        assert not s.is_valid()
        assert "valor_total" in s.errors
