"""Testes dos mixins multi-tenant: OrgQuerySetMixin e OrgCreateMixin.

Valida isolamento de dados entre organizacoes.
"""

import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Membership, Organization
from apps.empresas.models import Empresa

User = get_user_model()


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Org A", slug="org-a-mixin")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B", slug="org-b-mixin")


@pytest.fixture
def user_a(db, org_a):
    u = User.objects.create_user(username="usera_mix", email="usera@mix.com", password="testpass123")
    Membership.objects.create(user=u, organization=org_a)
    return u


@pytest.fixture
def user_b(db, org_b):
    u = User.objects.create_user(username="userb_mix", email="userb@mix.com", password="testpass123")
    Membership.objects.create(user=u, organization=org_b)
    return u


@pytest.fixture
def client_a(user_a):
    c = APIClient()
    c.login(username="usera_mix", password="testpass123")
    return c


@pytest.fixture
def client_b(user_b):
    c = APIClient()
    c.login(username="userb_mix", password="testpass123")
    return c


@pytest.mark.django_db
class TestOrgQuerySetMixin:
    """Testa OrgQuerySetMixin — filtra queryset por organization."""

    URL = "/api/v1/empresas/"

    def test_usuario_so_ve_empresas_da_sua_org(self, client_a, client_b, org_a, org_b):
        """Usuario da org A nao ve empresas da org B."""
        Empresa.objects.create(organization=org_a, nome="Empresa A", cnpj="11.111.111/0001-11", porte="ME/EPP")
        Empresa.objects.create(organization=org_b, nome="Empresa B", cnpj="22.222.222/0001-22", porte="DEMAIS")

        response_a = client_a.get(self.URL)
        assert response_a.status_code == 200
        results_a = response_a.json().get("results", response_a.json())
        assert len(results_a) == 1
        assert results_a[0]["nome"] == "Empresa A"

        response_b = client_b.get(self.URL)
        results_b = response_b.json().get("results", response_b.json())
        assert len(results_b) == 1
        assert results_b[0]["nome"] == "Empresa B"

    def test_usuario_sem_org_ve_lista_vazia(self, db):
        """Usuario sem membership nao ve nenhuma empresa."""
        _ = User.objects.create_user(username="orphan_mix", email="orphan@mix.com", password="testpass123")
        client = APIClient()
        client.login(username="orphan_mix", password="testpass123")

        response = client.get(self.URL)
        assert response.status_code == 200
        results = response.json().get("results", response.json())
        assert len(results) == 0


@pytest.mark.django_db
class TestOrgCreateMixin:
    """Testa OrgCreateMixin — seta organization automaticamente."""

    URL = "/api/v1/empresas/"

    def test_create_vincula_a_org_do_request(self, client_a, org_a):
        """Empresa criada eh vinculada a org do usuario autenticado."""
        payload = {
            "nome": "Nova Empresa",
            "cnpj": "33.333.333/0001-33",
            "porte": "ME/EPP",
            "honorarios_percentual": "0.15",
        }
        response = client_a.post(self.URL, payload, format="json")
        assert response.status_code == 201

        empresa = Empresa.objects.get(id=response.json()["id"])
        assert empresa.organization == org_a

    def test_create_sem_org_retorna_403(self, db):
        """Usuario sem org nao consegue criar empresa."""
        _ = User.objects.create_user(username="noorg_mix", email="noorg@mix.com", password="testpass123")
        client = APIClient()
        client.login(username="noorg_mix", password="testpass123")

        payload = {
            "nome": "Tentativa",
            "cnpj": "44.444.444/0001-44",
            "porte": "DEMAIS",
        }
        response = client.post(self.URL, payload, format="json")
        assert response.status_code == 403
