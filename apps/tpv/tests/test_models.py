"""Testes do model SimulacaoTPV.

Valida __str__, ordering e campos.
"""

from decimal import Decimal

import pytest

from apps.core.models import Organization
from apps.tpv.models import SimulacaoTPV


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Org TPV Model", slug="org-tpv-model")


@pytest.mark.django_db
class TestSimulacaoTPVModel:
    """Testa model SimulacaoTPV."""

    def test_str_com_nome(self, org):
        """__str__ mostra nome do contribuinte e tipo_porte."""
        sim = SimulacaoTPV.objects.create(
            organization=org,
            nome_contribuinte="Joao Silva",
            tipo_porte="PF",
            salario_minimo=Decimal("1621"),
            parcelas_entrada=5,
            parcelas_saldo=7,
        )
        assert "Joao Silva" in str(sim)
        assert "PF" in str(sim)

    def test_str_sem_nome(self, org):
        """__str__ mostra 'Sem nome' quando nome vazio."""
        sim = SimulacaoTPV.objects.create(
            organization=org,
            tipo_porte="ME",
            salario_minimo=Decimal("1621"),
            parcelas_entrada=5,
            parcelas_saldo=7,
        )
        assert "Sem nome" in str(sim)

    def test_ordering_created_at_desc(self, org):
        """Simulacoes TPV sao ordenadas por -created_at."""
        _ = SimulacaoTPV.objects.create(
            organization=org,
            nome_contribuinte="Primeiro",
            tipo_porte="PF",
            salario_minimo=Decimal("1621"),
            parcelas_entrada=5,
            parcelas_saldo=7,
        )
        _ = SimulacaoTPV.objects.create(
            organization=org,
            nome_contribuinte="Segundo",
            tipo_porte="ME",
            salario_minimo=Decimal("1621"),
            parcelas_entrada=3,
            parcelas_saldo=12,
        )
        simulacoes = list(SimulacaoTPV.objects.all())
        assert simulacoes[0].nome_contribuinte == "Segundo"

    def test_resultado_default_dict_vazio(self, org):
        """Campo resultado tem default dict vazio."""
        sim = SimulacaoTPV.objects.create(
            organization=org,
            tipo_porte="EPP",
            salario_minimo=Decimal("1621"),
            parcelas_entrada=5,
            parcelas_saldo=55,
        )
        assert sim.resultado == {}
