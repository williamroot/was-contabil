import uuid

import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Membership, Organization

User = get_user_model()


@pytest.fixture
def organization(db):
    """Cria organização de teste com UUID como PK."""
    org = Organization.objects.create(name="Escritório Teste", slug="escritorio-teste")
    assert isinstance(org.pk, uuid.UUID)  # Garante UUID
    return org


@pytest.fixture
def user(db, organization):
    """Cria usuário de teste vinculado a uma organização."""
    user = User.objects.create_user(username="testuser", email="test@test.com", password="testpass123")
    Membership.objects.create(user=user, organization=organization)
    return user


@pytest.fixture
def api_client(user):
    """APIClient autenticado via session (para que OrganizationMiddleware funcione)."""
    client = APIClient()
    client.login(username="testuser", password="testpass123")
    return client
