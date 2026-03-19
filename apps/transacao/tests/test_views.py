"""Testes de integração dos endpoints de simulação de transação tributária."""

import uuid

import pytest

from django.contrib.auth import get_user_model

from apps.core.models import Membership, Organization
from apps.transacao.models import Simulacao

User = get_user_model()


@pytest.fixture
def org_b(db):
    """Cria segunda organização para testes de isolamento."""
    return Organization.objects.create(name="Outro Escritório", slug="outro-escritorio")


@pytest.fixture
def user_b(db, org_b):
    """Cria usuário vinculado à organização B."""
    user = User.objects.create_user(
        username="userb",
        email="userb@test.com",
        password="testpass123",
    )
    Membership.objects.create(user=user, organization=org_b)
    return user


@pytest.fixture
def api_client_b(user_b):
    """APIClient autenticado via session com organização B."""
    from rest_framework.test import APIClient

    client = APIClient()
    client.login(username="userb", password="testpass123")
    return client


@pytest.fixture
def payload_basico():
    """Payload válido para simulação básica."""
    return {
        "valor_total_divida": "500000.00",
        "percentual_previdenciario": "0.3000",
        "is_me_epp": True,
        "classificacao": "D",
    }


@pytest.fixture
def payload_avancado():
    """Payload válido para simulação avançada."""
    return {
        "passivo_rfb": "200000.00",
        "passivo_pgfn": "300000.00",
        "capag_60m": "50000.00",
        "is_me_epp": True,
        "desconto_escolha": "MAIOR",
        "honorarios_percentual": "0.20",
        "previdenciario": {
            "principal": "50000.00",
            "multa": "10000.00",
            "juros": "15000.00",
            "encargos": "5000.00",
        },
        "tributario": {
            "principal": "80000.00",
            "multa": "20000.00",
            "juros": "30000.00",
            "encargos": "10000.00",
        },
    }


@pytest.mark.django_db
class TestSimularBasicoView:
    """Testes do endpoint POST /api/v1/transacao/simular/basico/."""

    URL = "/api/v1/transacao/simular/basico/"

    def test_simular_basico_retorna_200(self, api_client, payload_basico):
        """POST com dados válidos retorna 200 e resultado com cálculo."""
        response = api_client.post(self.URL, payload_basico, format="json")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        uuid.UUID(data["id"])  # Valida UUID
        assert "resultado" in data
        assert "calculo_detalhes" in data
        assert data["valor_total_divida"] == "500000.00"
        assert data["classificacao_credito"] == "D"

    def test_simular_basico_persiste_simulacao(self, api_client, payload_basico, organization):
        """POST cria Simulacao no banco vinculada à organização."""
        response = api_client.post(self.URL, payload_basico, format="json")

        assert response.status_code == 200
        simulacao = Simulacao.objects.get(id=response.json()["id"])
        assert simulacao.organization == organization

    def test_simular_basico_validacao_classificacao_invalida(self, api_client):
        """POST com classificação inválida retorna 400."""
        payload = {
            "valor_total_divida": "100000.00",
            "percentual_previdenciario": "0.0000",
            "classificacao": "Z",
        }
        response = api_client.post(self.URL, payload, format="json")

        assert response.status_code == 400


@pytest.mark.django_db
class TestSimularAvancadoView:
    """Testes do endpoint POST /api/v1/transacao/simular/avancado/."""

    URL = "/api/v1/transacao/simular/avancado/"

    def test_simular_avancado_retorna_200(self, api_client, payload_avancado):
        """POST com dados válidos retorna 200 e resultado com cálculo."""
        response = api_client.post(self.URL, payload_avancado, format="json")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        uuid.UUID(data["id"])
        assert "resultado" in data
        assert "calculo_detalhes" in data


@pytest.mark.django_db
class TestHistoricoView:
    """Testes do endpoint GET /api/v1/transacao/historico/."""

    URL_BASICO = "/api/v1/transacao/simular/basico/"
    URL_HISTORICO = "/api/v1/transacao/historico/"

    def test_historico_lista_simulacoes_da_org(self, api_client, payload_basico):
        """GET lista simulações criadas pela organização do usuário."""
        # Criar 2 simulações
        api_client.post(self.URL_BASICO, payload_basico, format="json")
        api_client.post(self.URL_BASICO, payload_basico, format="json")

        response = api_client.get(self.URL_HISTORICO)

        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 2

    def test_isolamento_multi_tenant_simulacoes(self, api_client, api_client_b, payload_basico):
        """Simulações da org A não aparecem na listagem da org B."""
        # Criar simulação na org A
        api_client.post(self.URL_BASICO, payload_basico, format="json")

        # Listar com client da org B — deve estar vazio
        response = api_client_b.get(self.URL_HISTORICO)

        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 0
