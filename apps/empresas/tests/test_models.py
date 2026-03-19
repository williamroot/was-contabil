"""Testes do model Empresa e EmpresaQuerySet.

Valida __str__, queryset customizado e busca por nome/CNPJ.
"""

import pytest

from django.contrib.auth import get_user_model

from apps.core.models import Organization
from apps.empresas.models import Empresa

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Org Empresa Test", slug="org-empresa-test")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B Empresa", slug="org-b-empresa")


@pytest.mark.django_db
class TestEmpresaModel:
    """Testa model Empresa."""

    def test_str_representation(self, org):
        """__str__ retorna 'nome (cnpj)'."""
        empresa = Empresa.objects.create(
            organization=org,
            nome="Alfa Consultoria",
            cnpj="11.111.111/0001-11",
            porte="ME/EPP",
        )
        assert str(empresa) == "Alfa Consultoria (11.111.111/0001-11)"

    def test_ordering_por_nome(self, org):
        """Empresas sao ordenadas por nome."""
        Empresa.objects.create(organization=org, nome="Zebra LTDA", cnpj="11.111.111/0001-11", porte="DEMAIS")
        Empresa.objects.create(organization=org, nome="Alfa SA", cnpj="22.222.222/0001-22", porte="ME/EPP")

        nomes = list(Empresa.objects.values_list("nome", flat=True))
        assert nomes == ["Alfa SA", "Zebra LTDA"]


@pytest.mark.django_db
class TestEmpresaQuerySet:
    """Testa queryset customizado da Empresa."""

    def test_da_organizacao(self, org, org_b):
        """da_organizacao filtra empresas da organizacao correta."""
        Empresa.objects.create(organization=org, nome="Empresa A", cnpj="11.111.111/0001-11", porte="ME/EPP")
        Empresa.objects.create(organization=org_b, nome="Empresa B", cnpj="22.222.222/0001-22", porte="DEMAIS")

        qs = Empresa.objects.da_organizacao(org)
        assert qs.count() == 1
        assert qs.first().nome == "Empresa A"

    def test_buscar_por_nome(self, org):
        """buscar() encontra empresa por nome (case-insensitive)."""
        Empresa.objects.create(organization=org, nome="Alfa Consultoria", cnpj="11.111.111/0001-11", porte="ME/EPP")
        Empresa.objects.create(organization=org, nome="Beta Advocacia", cnpj="22.222.222/0001-22", porte="DEMAIS")

        resultado = Empresa.objects.buscar(org, "alfa")
        assert resultado.count() == 1
        assert resultado.first().nome == "Alfa Consultoria"

    def test_buscar_por_cnpj(self, org):
        """buscar() encontra empresa por CNPJ."""
        Empresa.objects.create(organization=org, nome="Empresa X", cnpj="99.888.777/0001-66", porte="ME/EPP")

        resultado = Empresa.objects.buscar(org, "99.888")
        assert resultado.count() == 1

    def test_buscar_nao_retorna_outra_org(self, org, org_b):
        """buscar() nao retorna empresas de outra organizacao."""
        Empresa.objects.create(organization=org_b, nome="Alfa B", cnpj="33.333.333/0001-33", porte="ME/EPP")

        resultado = Empresa.objects.buscar(org, "Alfa")
        assert resultado.count() == 0
