"""Testes dos serializers de Empresa.

Valida CNPJ (14 digitos), porte (ME/EPP ou DEMAIS), e campos obrigatorios.
"""

from apps.empresas.serializers import EmpresaCreateSerializer


class TestEmpresaCreateSerializer:
    """Testa validacao do EmpresaCreateSerializer."""

    def _valid_payload(self, **overrides):
        payload = {
            "nome": "Empresa Teste LTDA",
            "cnpj": "11.111.111/0001-11",
            "porte": "ME/EPP",
            "honorarios_percentual": "0.15",
        }
        payload.update(overrides)
        return payload

    def test_payload_valido(self):
        """Payload completo valido eh aceito."""
        s = EmpresaCreateSerializer(data=self._valid_payload())
        assert s.is_valid(), s.errors

    def test_cnpj_14_digitos_com_pontuacao(self):
        """CNPJ com pontuacao (14 digitos) eh aceito."""
        s = EmpresaCreateSerializer(data=self._valid_payload(cnpj="12.345.678/0001-90"))
        assert s.is_valid(), s.errors

    def test_cnpj_14_digitos_sem_pontuacao(self):
        """CNPJ sem pontuacao (14 digitos) eh aceito."""
        s = EmpresaCreateSerializer(data=self._valid_payload(cnpj="12345678000190"))
        assert s.is_valid(), s.errors

    def test_cnpj_13_digitos_rejeita(self):
        """CNPJ com 13 digitos deve rejeitar."""
        s = EmpresaCreateSerializer(data=self._valid_payload(cnpj="1234567800019"))
        assert not s.is_valid()
        assert "cnpj" in s.errors

    def test_cnpj_15_digitos_rejeita(self):
        """CNPJ com 15 digitos deve rejeitar."""
        s = EmpresaCreateSerializer(data=self._valid_payload(cnpj="123456780001900"))
        assert not s.is_valid()
        assert "cnpj" in s.errors

    def test_cnpj_vazio_rejeita(self):
        """CNPJ vazio deve rejeitar."""
        s = EmpresaCreateSerializer(data=self._valid_payload(cnpj=""))
        assert not s.is_valid()
        assert "cnpj" in s.errors

    def test_porte_me_epp_valido(self):
        """Porte ME/EPP eh valido."""
        s = EmpresaCreateSerializer(data=self._valid_payload(porte="ME/EPP"))
        assert s.is_valid(), s.errors

    def test_porte_demais_valido(self):
        """Porte DEMAIS eh valido."""
        s = EmpresaCreateSerializer(data=self._valid_payload(porte="DEMAIS"))
        assert s.is_valid(), s.errors

    def test_porte_invalido_rejeita(self):
        """Porte PJ nao eh valido."""
        s = EmpresaCreateSerializer(data=self._valid_payload(porte="PJ"))
        assert not s.is_valid()
        assert "porte" in s.errors

    def test_porte_ltda_rejeita(self):
        """Porte LTDA nao eh valido."""
        s = EmpresaCreateSerializer(data=self._valid_payload(porte="LTDA"))
        assert not s.is_valid()
        assert "porte" in s.errors

    def test_nome_obrigatorio(self):
        """Nome eh campo obrigatorio."""
        payload = self._valid_payload()
        del payload["nome"]
        s = EmpresaCreateSerializer(data=payload)
        assert not s.is_valid()
        assert "nome" in s.errors
