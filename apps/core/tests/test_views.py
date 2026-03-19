"""Testes das views do core — HomeView, LoginPageView, InvitePageView.

Valida redirecionamento para login, acesso autenticado e pagina de convite.
"""

import pytest

from django.contrib.auth import get_user_model
from django.test import Client

from apps.core.models import Invitation, Membership, Organization

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Escritorio Teste", slug="escritorio-test-views")


@pytest.fixture
def test_user(db, org):
    u = User.objects.create_user(username="coreviewuser", email="coreview@test.com", password="testpass123")
    Membership.objects.create(user=u, organization=org)
    return u


@pytest.fixture
def authed_client(test_user):
    c = Client()
    c.login(username="coreviewuser", password="testpass123")
    return c


@pytest.fixture
def anon_client():
    return Client()


@pytest.mark.django_db
class TestLandingView:
    """Testa LandingView — landing page publica."""

    URL = "/"

    def test_anonimo_ve_landing(self, anon_client):
        """Visitante anonimo ve a landing page."""
        response = anon_client.get(self.URL)
        assert response.status_code == 200

    def test_autenticado_redireciona_para_dashboard(self, authed_client):
        """Usuario logado eh redirecionado para o dashboard."""
        response = authed_client.get(self.URL)
        assert response.status_code == 302
        assert "/dashboard/" in response.url


@pytest.mark.django_db
class TestHomeView:
    """Testa HomeView — dashboard (area logada)."""

    URL = "/dashboard/"

    def test_redireciona_para_login_se_nao_autenticado(self, anon_client):
        """Visitante anonimo eh redirecionado para login."""
        response = anon_client.get(self.URL)
        assert response.status_code in (301, 302)
        assert "login" in response.url or "accounts" in response.url

    def test_autenticado_retorna_200(self, authed_client):
        """Usuarios autenticados veem o dashboard (status 200)."""
        response = authed_client.get(self.URL)
        assert response.status_code == 200

    def test_usa_template_home(self, authed_client):
        """HomeView usa template core/home.html."""
        response = authed_client.get(self.URL)
        templates_usados = [t.name for t in response.templates]
        assert "core/home.html" in templates_usados


@pytest.mark.django_db
class TestLoginPageView:
    """Testa LoginPageView."""

    URL = "/login/"

    def test_login_page_acessivel(self, anon_client):
        """Pagina de login eh acessivel sem autenticacao."""
        response = anon_client.get(self.URL)
        assert response.status_code == 200


@pytest.mark.django_db
class TestInvitePageView:
    """Testa InvitePageView — pagina de convite por token."""

    def test_convite_valido_retorna_200(self, anon_client, org, test_user):
        """Token valido mostra pagina do convite."""
        from datetime import timedelta

        from django.utils import timezone

        invitation = Invitation.objects.create(
            email="convidado@test.com",
            token="abc123token",
            organization=org,
            invited_by=test_user,
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = anon_client.get(f"/convite/{invitation.token}/")
        assert response.status_code == 200

    def test_convite_token_invalido_mostra_erro(self, anon_client):
        """Token invalido retorna 200 com mensagem de erro no contexto."""
        response = anon_client.get("/convite/token-que-nao-existe/")
        assert response.status_code == 200
        assert response.context["error"] == "Convite inválido, expirado ou já utilizado"
        assert response.context["invitation"] is None

    def test_convite_expirado_mostra_erro(self, anon_client, org, test_user):
        """Convite expirado retorna 200 com mensagem de erro no contexto."""
        from datetime import timedelta

        from django.utils import timezone

        invitation = Invitation.objects.create(
            email="expirado@test.com",
            token="expired-token",
            organization=org,
            invited_by=test_user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        response = anon_client.get(f"/convite/{invitation.token}/")
        assert response.status_code == 200
        assert response.context["error"] == "Convite inválido, expirado ou já utilizado"
        assert response.context["invitation"] is None

    def test_convite_ja_aceito_mostra_erro(self, anon_client, org, test_user):
        """Convite ja aceito retorna 200 com mensagem de erro no contexto."""
        from datetime import timedelta

        from django.utils import timezone

        invitation = Invitation.objects.create(
            email="aceito@test.com",
            token="accepted-token",
            organization=org,
            invited_by=test_user,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),
        )
        response = anon_client.get(f"/convite/{invitation.token}/")
        assert response.status_code == 200
        assert response.context["error"] == "Convite inválido, expirado ou já utilizado"
        assert response.context["invitation"] is None
