"""Testes de integração do endpoint de comparação de modalidades."""

import pytest


@pytest.fixture
def payload_comparacao():
    """Payload válido para comparação de modalidades."""
    return {
        "valor_total": "500000.00",
        "percentual_previdenciario": "0.3000",
        "is_me_epp": True,
        "classificacao": "D",
        "tpv_elegivel": True,
    }


@pytest.mark.django_db
class TestCompararView:
    """Testes do endpoint POST /api/v1/comparador/comparar/."""

    URL = "/api/v1/comparador/comparar/"

    def test_comparar_retorna_recomendacao(self, api_client, payload_comparacao):
        """POST com dados válidos retorna recomendação de modalidade."""
        response = api_client.post(self.URL, payload_comparacao, format="json")

        assert response.status_code == 200
        data = response.json()
        assert "recomendacao" in data
        assert data["recomendacao"] in ("TPV", "CAPACIDADE")
        assert "capacidade_valor_final" in data
        assert "capacidade_economia" in data
        assert "tpv_disponivel" in data
        assert data["tpv_disponivel"] is True

    def test_comparar_sem_tpv_recomenda_capacidade(self, api_client):
        """POST com tpv_elegivel=False recomenda CAPACIDADE."""
        payload = {
            "valor_total": "500000.00",
            "percentual_previdenciario": "0.3000",
            "is_me_epp": False,
            "classificacao": "D",
            "tpv_elegivel": False,
        }
        response = api_client.post(self.URL, payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["recomendacao"] == "CAPACIDADE"
        assert data["tpv_disponivel"] is False
