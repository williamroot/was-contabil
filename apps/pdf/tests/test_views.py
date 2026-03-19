"""Testes das views de download de PDF.

Valida que cada view:
1. Retorna 404 quando simulacao nao encontrada no banco
2. Redireciona para login quando nao autenticado (LoginRequiredMixin)
3. Retorna PDF valido quando simulacao existe no banco
4. Content-Type e Content-Disposition corretos
5. Multi-tenant: nao retorna simulacao de outra organization
"""

import uuid

import pytest

from django.contrib.auth import get_user_model
from django.test import Client

from apps.core.models import Membership, Organization
from apps.tpv.models import SimulacaoTPV
from apps.transacao.models import Simulacao, SimulacaoAvancada

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def organization(db):
    """Cria organizacao de teste."""
    return Organization.objects.create(name="Teste PDF", slug="teste-pdf")


@pytest.fixture
def other_organization(db):
    """Cria outra organizacao para testar multi-tenant."""
    return Organization.objects.create(name="Outra Org", slug="outra-org")


@pytest.fixture
def user_with_org(db, organization):
    """Cria usuario vinculado a organizacao."""
    user = User.objects.create_user(username="pdfuser", email="pdf@test.com", password="testpass123")
    Membership.objects.create(user=user, organization=organization)
    return user


@pytest.fixture
def authenticated_client(user_with_org, settings):
    """Client Django autenticado com middleware adequado."""
    settings.SECURE_SSL_REDIRECT = False
    settings.MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "apps.core.middleware.OrganizationMiddleware",
    ]
    client = Client()
    client.login(username="pdfuser", password="testpass123")
    return client


@pytest.fixture
def unauthenticated_client(settings):
    """Client Django sem autenticacao."""
    settings.SECURE_SSL_REDIRECT = False
    settings.MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "apps.core.middleware.OrganizationMiddleware",
    ]
    return Client()


@pytest.fixture
def simulacao_basica(organization):
    """Cria Simulacao basica no banco com resultado preenchido."""
    return Simulacao.objects.create(
        organization=organization,
        razao_social="Empresa Teste",
        cnpj="12.345.678/0001-00",
        valor_total_divida=100000,
        percentual_previdenciario=0.30,
        is_me_epp=False,
        classificacao_credito="D",
        resultado={
            "valor_original": "100000",
            "valor_desconto": "65000",
            "valor_com_desconto": "35000",
            "valor_entrada": "6000",
            "num_parcelas_entrada": 6,
            "valor_parcela_entrada": "1000",
            "saldo_apos_entrada": "29000",
            "classificacao": "D",
            "is_me_epp": False,
            "percentual_previdenciario": 30,
            "modalidades": [
                {
                    "nome": "Previdenciario",
                    "is_previdenciario": True,
                    "valor": "8700",
                    "num_parcelas": 54,
                    "valor_parcela": "161.11",
                    "prazo_maximo": 60,
                },
            ],
            "fluxo": [],
        },
    )


@pytest.fixture
def simulacao_avancada(organization):
    """Cria SimulacaoAvancada no banco com resultado preenchido."""
    return SimulacaoAvancada.objects.create(
        organization=organization,
        passivo_rfb=50000,
        capag_60m=1000,
        desconto_escolha="MAIOR",
        resultado={
            "rating": "D",
            "desconto_percentual": "0.65",
            "desconto_total": "45500",
            "desconto_efetivo": "45500",
            "passivos": {
                "rfb": "50000",
                "pgfn": "100000",
                "total": "150000",
                "saldo": "54500",
            },
            "honorarios": "9100",
            "honorarios_percentual": "0.20",
            "previdenciario": {
                "nome": "Previdenciario",
                "componentes": {
                    "principal": "20000",
                    "multa": "10000",
                    "juros": "8000",
                    "encargos": "2000",
                },
                "desconto_result": {
                    "principal_final": "20000",
                    "principal_desconto": "0",
                    "multa_final": "3500",
                    "multa_desconto": "6500",
                    "juros_final": "2800",
                    "juros_desconto": "5200",
                    "encargos_final": "700",
                    "encargos_desconto": "1300",
                    "total_desconto": "13000",
                    "total_final": "27000",
                },
                "prazo_total": 60,
                "entrada": 6,
                "parcelas": 54,
                "saldo": "27000",
                "fluxo": [],
            },
            "tributario": {
                "nome": "Tributario",
                "componentes": {
                    "principal": "30000",
                    "multa": "15000",
                    "juros": "12000",
                    "encargos": "3000",
                },
                "desconto_result": {
                    "principal_final": "30000",
                    "principal_desconto": "0",
                    "multa_final": "5250",
                    "multa_desconto": "9750",
                    "juros_final": "4200",
                    "juros_desconto": "7800",
                    "encargos_final": "1050",
                    "encargos_desconto": "1950",
                    "total_desconto": "19500",
                    "total_final": "40500",
                },
                "prazo_total": 120,
                "entrada": 6,
                "parcelas": 114,
                "saldo": "40500",
                "fluxo": [],
            },
            "simples": None,
            "is_me_epp": False,
        },
    )


@pytest.fixture
def simulacao_tpv(organization):
    """Cria SimulacaoTPV no banco com resultado preenchido."""
    return SimulacaoTPV.objects.create(
        organization=organization,
        nome_contribuinte="Joao da Silva",
        cpf_cnpj="123.456.789-00",
        tipo_porte="PF",
        salario_minimo=1621,
        parcelas_entrada=5,
        parcelas_saldo=7,
        resultado={
            "total_cdas_aptas": "5000",
            "cdas_aptas": [
                {
                    "numero": "CDA-001",
                    "valor": "3000",
                    "data_inscricao": "2020-03-15",
                    "validacao": {"apta": True, "motivos": []},
                },
            ],
            "cdas_nao_aptas": [],
            "entrada": "250",
            "desconto": "0.50",
            "saldo": "2375",
            "valor_final": "2625",
            "economia": "2375",
            "parcelas_entrada": 5,
            "valor_parcela_entrada": "50",
            "parcelas_saldo": 7,
            "valor_parcela_saldo": "339.29",
            "fluxo": [],
        },
    )


# ---------------------------------------------------------------------------
# Testes: DiagnosticoPDFView
# ---------------------------------------------------------------------------


class TestDiagnosticoPDFView:
    """Testa view de download do PDF de diagnostico."""

    @pytest.mark.django_db
    def test_retorna_404_sem_simulacao_no_banco(self, authenticated_client):
        """GET com UUID inexistente deve retornar 404."""
        test_uuid = uuid.uuid4()
        response = authenticated_client.get(f"/pdf/diagnostico/{test_uuid}/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_redireciona_sem_autenticacao(self, unauthenticated_client, simulacao_basica):
        """GET sem autenticacao deve redirecionar para login."""
        response = unauthenticated_client.get(f"/pdf/diagnostico/{simulacao_basica.id}/")
        assert response.status_code == 302
        assert "/accounts/login/" in response.url or "/login/" in response.url

    @pytest.mark.django_db
    def test_retorna_pdf_com_simulacao_no_banco(self, authenticated_client, simulacao_basica):
        """GET com simulacao existente no banco deve retornar PDF valido."""
        response = authenticated_client.get(f"/pdf/diagnostico/{simulacao_basica.id}/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "attachment" in response["Content-Disposition"]
        assert response.content[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_multi_tenant_nao_retorna_simulacao_de_outra_org(self, authenticated_client, other_organization):
        """GET com simulacao de outra org deve retornar 404."""
        simulacao_outra = Simulacao.objects.create(
            organization=other_organization,
            valor_total_divida=10000,
            percentual_previdenciario=0.30,
            resultado={"valor_original": "10000", "modalidades": [], "fluxo": []},
        )
        response = authenticated_client.get(f"/pdf/diagnostico/{simulacao_outra.id}/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Testes: SimulacaoAvancadaPDFView
# ---------------------------------------------------------------------------


class TestSimulacaoAvancadaPDFView:
    """Testa view de download do PDF de simulacao avancada."""

    @pytest.mark.django_db
    def test_retorna_404_sem_simulacao_no_banco(self, authenticated_client):
        """GET com UUID inexistente deve retornar 404."""
        test_uuid = uuid.uuid4()
        response = authenticated_client.get(f"/pdf/simulacao-avancada/{test_uuid}/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_retorna_pdf_modo_resumido(self, authenticated_client, simulacao_avancada):
        """GET modo=resumido deve retornar PDF resumido."""
        response = authenticated_client.get(f"/pdf/simulacao-avancada/{simulacao_avancada.id}/?modo=resumido")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "resumido" in response["Content-Disposition"]
        assert response.content[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_retorna_pdf_modo_completo(self, authenticated_client, simulacao_avancada):
        """GET modo=completo deve retornar PDF completo."""
        response = authenticated_client.get(f"/pdf/simulacao-avancada/{simulacao_avancada.id}/?modo=completo")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "completo" in response["Content-Disposition"]
        assert response.content[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_modo_padrao_resumido(self, authenticated_client, simulacao_avancada):
        """GET sem parametro modo deve usar resumido como padrao."""
        response = authenticated_client.get(f"/pdf/simulacao-avancada/{simulacao_avancada.id}/")
        assert response.status_code == 200
        assert "resumido" in response["Content-Disposition"]

    @pytest.mark.django_db
    def test_redireciona_sem_autenticacao(self, unauthenticated_client, simulacao_avancada):
        """GET sem autenticacao deve redirecionar para login."""
        response = unauthenticated_client.get(f"/pdf/simulacao-avancada/{simulacao_avancada.id}/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Testes: TPVPDFView
# ---------------------------------------------------------------------------


class TestTPVPDFView:
    """Testa view de download do PDF de relatorio TPV."""

    @pytest.mark.django_db
    def test_retorna_404_sem_simulacao_no_banco(self, authenticated_client):
        """GET com UUID inexistente deve retornar 404."""
        test_uuid = uuid.uuid4()
        response = authenticated_client.get(f"/pdf/tpv/{test_uuid}/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_retorna_pdf_com_simulacao_no_banco(self, authenticated_client, simulacao_tpv):
        """GET com simulacao existente no banco deve retornar PDF valido."""
        response = authenticated_client.get(f"/pdf/tpv/{simulacao_tpv.id}/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert f"tpv_{simulacao_tpv.id}.pdf" in response["Content-Disposition"]
        assert response.content[:5] == b"%PDF-"

    @pytest.mark.django_db
    def test_redireciona_sem_autenticacao(self, unauthenticated_client, simulacao_tpv):
        """GET sem autenticacao deve redirecionar para login."""
        response = unauthenticated_client.get(f"/pdf/tpv/{simulacao_tpv.id}/")
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_multi_tenant_nao_retorna_tpv_de_outra_org(self, authenticated_client, other_organization):
        """GET com simulacao TPV de outra org deve retornar 404."""
        tpv_outra = SimulacaoTPV.objects.create(
            organization=other_organization,
            tipo_porte="PF",
            salario_minimo=1621,
            parcelas_entrada=5,
            parcelas_saldo=7,
            resultado={
                "total_cdas_aptas": "1000",
                "cdas_aptas": [],
                "cdas_nao_aptas": [],
                "entrada": "50",
                "desconto": "0.50",
                "saldo": "475",
                "valor_final": "525",
                "economia": "475",
                "parcelas_entrada": 5,
                "valor_parcela_entrada": "10",
                "parcelas_saldo": 7,
                "valor_parcela_saldo": "67.86",
                "fluxo": [],
            },
        )
        response = authenticated_client.get(f"/pdf/tpv/{tpv_outra.id}/")
        assert response.status_code == 404
