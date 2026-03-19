"""Testes do CRUD de Empresa com isolamento multi-tenant."""

import uuid

import pytest

from django.contrib.auth import get_user_model

from apps.core.models import Membership, Organization

User = get_user_model()


@pytest.fixture
def empresa_payload():
    """Payload válido para criar uma empresa."""
    return {
        "nome": "Sítio do Picapau Amarelo LTDA",
        "cnpj": "03.523.834/0001-90",
        "porte": "ME/EPP",
        "honorarios_percentual": "10.00",
        "observacoes": "Empresa rural",
    }


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


@pytest.mark.django_db
class TestEmpresaCRUD:
    """Testes do CRUD completo de Empresa."""

    URL = "/api/v1/empresas/"

    def test_criar_empresa(self, api_client, empresa_payload):
        """POST com dados válidos retorna 201 e UUID."""
        response = api_client.post(self.URL, empresa_payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        # Valida que o id é um UUID válido
        uuid.UUID(data["id"])
        assert data["nome"] == empresa_payload["nome"]
        assert data["cnpj"] == empresa_payload["cnpj"]
        assert data["porte"] == empresa_payload["porte"]

    def test_listar_empresas(self, api_client, empresa_payload):
        """GET lista só empresas da mesma organização."""
        # Cria duas empresas
        api_client.post(self.URL, empresa_payload, format="json")
        payload2 = {**empresa_payload, "nome": "Empresa 2", "cnpj": "12.345.678/0001-90"}
        api_client.post(self.URL, payload2, format="json")

        response = api_client.get(self.URL)

        assert response.status_code == 200
        data = response.json()
        # DRF paginado
        results = data.get("results", data)
        assert len(results) == 2

    def test_buscar_por_nome(self, api_client, empresa_payload):
        """GET com ?busca=Sítio filtra por nome."""
        api_client.post(self.URL, empresa_payload, format="json")
        payload2 = {**empresa_payload, "nome": "Empresa XYZ", "cnpj": "12.345.678/0001-90"}
        api_client.post(self.URL, payload2, format="json")

        response = api_client.get(self.URL, {"busca": "Sítio"})

        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 1
        assert "Sítio" in results[0]["nome"]

    def test_buscar_por_cnpj(self, api_client, empresa_payload):
        """GET com ?busca=03.523 filtra por CNPJ."""
        api_client.post(self.URL, empresa_payload, format="json")
        payload2 = {**empresa_payload, "nome": "Empresa XYZ", "cnpj": "12.345.678/0001-90"}
        api_client.post(self.URL, payload2, format="json")

        response = api_client.get(self.URL, {"busca": "03.523"})

        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 1
        assert results[0]["cnpj"] == empresa_payload["cnpj"]

    def test_atualizar_empresa(self, api_client, empresa_payload):
        """PUT atualiza nome e porte."""
        response = api_client.post(self.URL, empresa_payload, format="json")
        empresa_id = response.json()["id"]

        update_payload = {**empresa_payload, "nome": "Novo Nome LTDA", "porte": "DEMAIS"}
        response = api_client.put(f"{self.URL}{empresa_id}/", update_payload, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Novo Nome LTDA"
        assert data["porte"] == "DEMAIS"

    def test_excluir_empresa(self, api_client, empresa_payload):
        """DELETE retorna 204."""
        response = api_client.post(self.URL, empresa_payload, format="json")
        empresa_id = response.json()["id"]

        response = api_client.delete(f"{self.URL}{empresa_id}/")

        assert response.status_code == 204

        # Confirma que foi excluída
        response = api_client.get(f"{self.URL}{empresa_id}/")
        assert response.status_code == 404

    def test_isolamento_multi_tenant(self, api_client, api_client_b, empresa_payload):
        """Empresa da org A não aparece na org B."""
        # Cria empresa na org A
        api_client.post(self.URL, empresa_payload, format="json")

        # Lista com client da org B — deve estar vazio
        response = api_client_b.get(self.URL)

        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data)
        assert len(results) == 0

    def test_empresa_com_honorarios(self, api_client, empresa_payload):
        """Criar com honorarios_percentual=20 retorna 20."""
        empresa_payload["honorarios_percentual"] = "20.00"
        response = api_client.post(self.URL, empresa_payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["honorarios_percentual"] == "20.00"
