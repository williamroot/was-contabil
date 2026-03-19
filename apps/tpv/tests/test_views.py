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


@pytest.fixture
def empresa(organization):
    """Cria empresa de teste."""
    from apps.empresas.models import Empresa

    return Empresa.objects.create(
        organization=organization,
        nome="Sitio Verde LTDA",
        cnpj="03.523.294/0001-24",
        porte="ME/EPP",
        honorarios_percentual=20,
    )


@pytest.mark.django_db
class TestTPVComEmpresa:
    """Testes de vinculacao empresa <-> TPV."""

    URL = "/api/v1/tpv/simular/"

    def test_simular_com_empresa_preenche_nome_cnpj(self, api_client, empresa):
        """Quando empresa_id informado, nome e CNPJ vem da empresa."""
        payload = {
            "empresa_id": str(empresa.id),
            "tipo_porte": "ME",
            "salario_minimo": "1621.00",
            "parcelas_entrada": 1,
            "parcelas_saldo": 7,
            "cdas": [
                {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "2024-01-15"},
            ],
        }
        response = api_client.post(self.URL, payload, content_type="application/json")
        assert response.status_code == 200

        from apps.tpv.models import SimulacaoTPV

        sim = SimulacaoTPV.objects.last()
        assert sim.empresa == empresa
        assert sim.nome_contribuinte == "Sitio Verde LTDA"
        assert sim.cpf_cnpj == "03.523.294/0001-24"

    def test_simular_sem_empresa_usa_campos_manuais(self, api_client):
        """Sem empresa_id, nome e CNPJ vem do payload."""
        payload = {
            "nome_contribuinte": "Manual da Silva",
            "cpf_cnpj": "111.222.333-44",
            "tipo_porte": "PF",
            "salario_minimo": "1621.00",
            "parcelas_entrada": 1,
            "parcelas_saldo": 7,
            "cdas": [
                {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "2024-01-15"},
            ],
        }
        response = api_client.post(self.URL, payload, content_type="application/json")
        assert response.status_code == 200

        from apps.tpv.models import SimulacaoTPV

        sim = SimulacaoTPV.objects.last()
        assert sim.empresa is None
        assert sim.nome_contribuinte == "Manual da Silva"
        assert sim.cpf_cnpj == "111.222.333-44"

    def test_simular_com_empresa_de_outra_org_ignora(self, api_client):
        """Empresa de outra org nao vincula (seguranca multi-tenant)."""
        from apps.core.models import Organization
        from apps.empresas.models import Empresa

        outra_org = Organization.objects.create(name="Outra Org", slug="outra-org")
        empresa_outra = Empresa.objects.create(
            organization=outra_org,
            nome="Empresa Alheia",
            cnpj="99.999.999/0001-99",
            porte="DEMAIS",
        )
        payload = {
            "empresa_id": str(empresa_outra.id),
            "nome_contribuinte": "Fallback",
            "cpf_cnpj": "000.000.000-00",
            "tipo_porte": "PF",
            "salario_minimo": "1621.00",
            "parcelas_entrada": 1,
            "parcelas_saldo": 7,
            "cdas": [
                {"numero": "CDA-001", "valor": "50000.00", "data_inscricao": "2024-01-15"},
            ],
        }
        response = api_client.post(self.URL, payload, content_type="application/json")
        assert response.status_code == 200

        from apps.tpv.models import SimulacaoTPV

        sim = SimulacaoTPV.objects.last()
        # Empresa de outra org nao vincula — usa fallback manual
        assert sim.empresa is None
        assert sim.nome_contribuinte == "Fallback"
