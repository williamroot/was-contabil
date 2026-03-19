"""Testes das views de indices economicos (SELIC).

Valida endpoints GET de ultimos indices e SELIC acumulada.
"""

from datetime import date
from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Membership, Organization
from apps.indices.models import IndiceEconomico

User = get_user_model()


@pytest.fixture
def org_indices(db):
    return Organization.objects.create(name="Org Indices", slug="org-indices-test")


@pytest.fixture
def user_indices(db, org_indices):
    u = User.objects.create_user(username="indicesuser", email="indices@test.com", password="testpass123")
    Membership.objects.create(user=u, organization=org_indices)
    return u


@pytest.fixture
def client_indices(user_indices):
    c = APIClient()
    c.login(username="indicesuser", password="testpass123")
    return c


@pytest.fixture
def selic_data(db):
    """Cria registros SELIC no banco."""
    IndiceEconomico.objects.create(
        serie_codigo=4390,
        serie_nome="SELIC mensal",
        data_referencia=date(2026, 1, 1),
        valor=Decimal("0.870000"),
    )
    IndiceEconomico.objects.create(
        serie_codigo=4390,
        serie_nome="SELIC mensal",
        data_referencia=date(2026, 2, 1),
        valor=Decimal("0.820000"),
    )


@pytest.mark.django_db
class TestSelicUltimosView:
    """Testa GET /api/v1/indices/selic/ultimos/."""

    URL = "/api/v1/indices/selic/ultimos/"

    def test_retorna_200_autenticado(self, client_indices, selic_data):
        """Retorna 200 para usuario autenticado."""
        response = client_indices.get(self.URL)
        assert response.status_code == 200

    def test_retorna_lista_de_indices(self, client_indices, selic_data):
        """Retorna lista de indices SELIC."""
        response = client_indices.get(self.URL)
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_nao_autenticado_retorna_403(self, db):
        """Visitante anonimo recebe 403."""
        client = APIClient()
        response = client.get(self.URL)
        assert response.status_code in (401, 403)

    def test_parametro_n_limita_resultados(self, client_indices, selic_data):
        """Parametro n=1 retorna apenas 1 indice."""
        response = client_indices.get(f"{self.URL}?n=1")
        data = response.json()
        assert len(data) == 1


@pytest.mark.django_db
class TestSelicAcumuladaView:
    """Testa GET /api/v1/indices/selic/acumulada/."""

    URL = "/api/v1/indices/selic/acumulada/"

    def test_retorna_200_com_datas(self, client_indices, selic_data):
        """Retorna 200 com datas validas."""
        response = client_indices.get(f"{self.URL}?data_inicial=2026-01-01&data_final=2026-02-28")
        assert response.status_code == 200
        data = response.json()
        assert "fator_acumulado" in data

    def test_sem_parametros_retorna_400(self, client_indices):
        """Sem parametros obrigatorios retorna 400."""
        response = client_indices.get(self.URL)
        assert response.status_code == 400

    def test_formato_data_invalido_retorna_400(self, client_indices):
        """Formato de data invalido retorna 400."""
        response = client_indices.get(f"{self.URL}?data_inicial=01/01/2026&data_final=28/02/2026")
        assert response.status_code == 400

    def test_sem_dados_retorna_fator_1(self, client_indices, db):
        """Sem dados no periodo, fator acumulado eh 1."""
        response = client_indices.get(f"{self.URL}?data_inicial=2020-01-01&data_final=2020-12-31")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["fator_acumulado"]) == Decimal("1")
