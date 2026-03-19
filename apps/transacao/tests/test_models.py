"""Testes dos models de transacao tributaria.

Valida __str__, ordering e campos obrigatorios.
"""

from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model

from apps.core.models import Organization
from apps.empresas.models import Empresa
from apps.transacao.models import Simulacao, SimulacaoAvancada

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Org Transacao", slug="org-transacao-test")


@pytest.fixture
def empresa(db, org):
    return Empresa.objects.create(
        organization=org,
        nome="Empresa Teste",
        cnpj="11.111.111/0001-11",
        porte="ME/EPP",
    )


@pytest.mark.django_db
class TestSimulacaoModel:
    """Testa model Simulacao (basica)."""

    def test_str_com_razao_social(self, org):
        """__str__ mostra razao social e valor."""
        sim = Simulacao.objects.create(
            organization=org,
            razao_social="Alfa LTDA",
            valor_total_divida=Decimal("100000"),
            percentual_previdenciario=Decimal("0.30"),
        )
        assert "Alfa LTDA" in str(sim)
        assert "100000" in str(sim)

    def test_str_sem_razao_social(self, org):
        """__str__ mostra 'Sem nome' quando razao social vazia."""
        sim = Simulacao.objects.create(
            organization=org,
            valor_total_divida=Decimal("50000"),
            percentual_previdenciario=Decimal("0.20"),
        )
        assert "Sem nome" in str(sim)

    def test_ordering_created_at_desc(self, org):
        """Simulacoes sao ordenadas por -created_at (mais recente primeiro)."""
        _ = Simulacao.objects.create(
            organization=org,
            razao_social="Primeira",
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("0.30"),
        )
        _ = Simulacao.objects.create(
            organization=org,
            razao_social="Segunda",
            valor_total_divida=Decimal("20000"),
            percentual_previdenciario=Decimal("0.40"),
        )
        simulacoes = list(Simulacao.objects.all())
        # Mais recente primeiro
        assert simulacoes[0].razao_social == "Segunda"

    def test_empresa_opcional(self, org):
        """Empresa eh campo opcional (simulacao rapida)."""
        sim = Simulacao.objects.create(
            organization=org,
            valor_total_divida=Decimal("50000"),
            percentual_previdenciario=Decimal("0.20"),
        )
        assert sim.empresa is None

    def test_empresa_vinculada(self, org, empresa):
        """Simulacao pode ser vinculada a uma empresa."""
        sim = Simulacao.objects.create(
            organization=org,
            empresa=empresa,
            valor_total_divida=Decimal("50000"),
            percentual_previdenciario=Decimal("0.20"),
        )
        assert sim.empresa == empresa


@pytest.mark.django_db
class TestSimulacaoAvancadaModel:
    """Testa model SimulacaoAvancada."""

    def test_str_com_empresa(self, org, empresa):
        """__str__ mostra nome da empresa."""
        sim = SimulacaoAvancada.objects.create(
            organization=org,
            empresa=empresa,
            passivo_rfb=Decimal("5000"),
            capag_60m=Decimal("1000"),
        )
        assert "Empresa Teste" in str(sim)

    def test_str_sem_empresa(self, org):
        """__str__ mostra 'Sem empresa' quando empresa eh None."""
        sim = SimulacaoAvancada.objects.create(
            organization=org,
            passivo_rfb=Decimal("5000"),
            capag_60m=Decimal("1000"),
        )
        assert "Sem empresa" in str(sim)

    def test_campos_pmje_default_zero(self, org):
        """Campos P/M/J/E tem default 0."""
        sim = SimulacaoAvancada.objects.create(
            organization=org,
            passivo_rfb=Decimal("5000"),
            capag_60m=Decimal("1000"),
        )
        assert sim.previdenciario_principal == 0
        assert sim.tributario_multa == 0
        assert sim.simples_juros == 0
