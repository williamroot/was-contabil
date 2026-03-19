"""Testes de integração dos endpoints TPV — Transação de Pequeno Valor."""

import io
import uuid

import pytest


@pytest.fixture
def payload_tpv():
    """Payload válido para simulação TPV."""
    return {
        "nome_contribuinte": "João da Silva",
        "cpf_cnpj": "123.456.789-00",
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
            {
                "numero": "CDA-002",
                "valor": "30000.00",
                "data_inscricao": "2024-06-01",
            },
        ],
    }


@pytest.fixture
def payload_wizard():
    """Payload válido para wizard de elegibilidade TPV."""
    return {
        "tipo_contribuinte": "PF",
        "possui_cda_acima_limite": False,
        "valor_total": "80000.00",
        "todas_cdas_mais_1_ano": True,
        "salario_minimo": "1621.00",
    }


@pytest.mark.django_db
class TestSimularTPVView:
    """Testes do endpoint POST /api/v1/tpv/simular/."""

    URL = "/api/v1/tpv/simular/"

    def test_simular_tpv_retorna_200(self, api_client, payload_tpv):
        """POST com dados válidos retorna 200 e resultado."""
        response = api_client.post(self.URL, payload_tpv, format="json")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        uuid.UUID(data["id"])
        assert "resultado" in data
        assert data["tipo_porte"] == "PF"


@pytest.mark.django_db
class TestWizardElegibilidadeView:
    """Testes do endpoint POST /api/v1/tpv/wizard/."""

    URL = "/api/v1/tpv/wizard/"

    def test_wizard_elegivel_retorna_faixas(self, api_client, payload_wizard):
        """POST com contribuinte elegível retorna faixas de desconto."""
        response = api_client.post(self.URL, payload_wizard, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["elegivel"] is True
        assert "faixas" in data
        assert "criterios" in data

    def test_wizard_nao_elegivel_sem_faixas(self, api_client):
        """POST com PJ (não elegível) não retorna faixas."""
        payload = {
            "tipo_contribuinte": "PJ",
            "possui_cda_acima_limite": False,
            "valor_total": "80000.00",
            "todas_cdas_mais_1_ano": True,
            "salario_minimo": "1621.00",
        }
        response = api_client.post(self.URL, payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["elegivel"] is False
        assert "faixas" not in data


@pytest.mark.django_db
class TestImportarCDAsView:
    """Testes do endpoint POST /api/v1/tpv/importar/."""

    URL = "/api/v1/tpv/importar/"

    def test_importar_csv_retorna_cdas(self, api_client):
        """POST com CSV válido retorna CDAs parseadas."""
        csv_content = "numero_cda,valor,data_inscricao\nCDA-001,50000,15/01/2024\nCDA-002,30000,01/06/2024\n"
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "cdas.csv"

        response = api_client.post(
            self.URL,
            {"arquivo": csv_file},
            format="multipart",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["cdas"]) == 2
        assert data["erros"] == []

    def test_importar_sem_arquivo_retorna_400(self, api_client):
        """POST sem arquivo retorna 400."""
        response = api_client.post(self.URL, {}, format="multipart")

        assert response.status_code == 400
