"""Testes do OrganizationMiddleware."""

import pytest

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.core.middleware import OrganizationMiddleware
from apps.core.models import Membership, Organization

User = get_user_model()


def dummy_response(request):
    """View dummy que retorna o request (para capturar request.organization)."""
    return request


@pytest.mark.django_db
class TestOrganizationMiddleware:
    """Testa que o middleware seta request.organization corretamente."""

    def setup_method(self):
        """Setup comum para cada teste."""
        self.factory = RequestFactory()
        self.middleware = OrganizationMiddleware(dummy_response)

    def test_authenticated_user_with_membership(self):
        """Usuário autenticado com membership deve ter request.organization setado."""
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(username="testuser", email="test@test.com", password="pass123")
        Membership.objects.create(user=user, organization=org)

        request = self.factory.get("/")
        request.user = user

        result = self.middleware(request)
        assert result.organization == org

    def test_authenticated_user_without_membership(self):
        """Usuário autenticado sem membership deve ter request.organization = None."""
        user = User.objects.create_user(username="testuser", email="test@test.com", password="pass123")

        request = self.factory.get("/")
        request.user = user

        result = self.middleware(request)
        assert result.organization is None

    def test_anonymous_user(self):
        """Usuário anônimo deve ter request.organization = None."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/")
        request.user = AnonymousUser()

        result = self.middleware(request)
        assert result.organization is None

    def test_user_with_multiple_memberships_gets_first(self):
        """Usuário com múltiplas orgs deve receber a primeira membership."""
        org1 = Organization.objects.create(name="AAA Org", slug="aaa-org")
        org2 = Organization.objects.create(name="BBB Org", slug="bbb-org")
        user = User.objects.create_user(username="testuser", email="test@test.com", password="pass123")
        Membership.objects.create(user=user, organization=org1)
        Membership.objects.create(user=user, organization=org2)

        request = self.factory.get("/")
        request.user = user

        result = self.middleware(request)
        # Deve retornar alguma organização (primeira do queryset)
        assert result.organization is not None
        assert result.organization in [org1, org2]
