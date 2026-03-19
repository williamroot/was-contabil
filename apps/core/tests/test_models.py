"""Testes dos models core: UUIDModel, Organization, Membership."""

import uuid

import pytest

from django.contrib.auth import get_user_model

from apps.core.models import Invitation, Membership, Organization, UUIDModel

User = get_user_model()


@pytest.mark.django_db
class TestUUIDModel:
    """Testa que todos os models usam UUID como primary key."""

    def test_organization_pk_is_uuid(self):
        org = Organization.objects.create(name="Test", slug="test")
        assert isinstance(org.pk, uuid.UUID)

    def test_membership_pk_is_uuid(self):
        org = Organization.objects.create(name="Test", slug="test")
        user = User.objects.create_user(username="u", email="u@t.com", password="pass123")
        m = Membership.objects.create(user=user, organization=org)
        assert isinstance(m.pk, uuid.UUID)

    def test_all_models_inherit_uuid_model(self):
        assert issubclass(Organization, UUIDModel)
        assert issubclass(Membership, UUIDModel)
        assert issubclass(Invitation, UUIDModel)


@pytest.mark.django_db
class TestOrganization:
    """Testa CRUD e constraints do model Organization."""

    def test_create_organization(self):
        org = Organization.objects.create(name="Escritório ABC", slug="escritorio-abc")
        assert org.name == "Escritório ABC"
        assert str(org) == "Escritório ABC"
        assert isinstance(org.id, uuid.UUID)

    def test_slug_unique(self):
        Organization.objects.create(name="Org 1", slug="org-1")
        with pytest.raises(Exception):
            Organization.objects.create(name="Org 2", slug="org-1")


@pytest.mark.django_db
class TestMembership:
    """Testa vínculo usuário-organização e constraints."""

    def test_user_belongs_to_organization(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(username="testuser", email="user@test.com", password="pass123")
        membership = Membership.objects.create(user=user, organization=org, is_owner=True)

        assert membership.user == user
        assert membership.organization == org
        assert membership.is_owner is True

    def test_user_cannot_join_same_org_twice(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(username="testuser", email="user@test.com", password="pass123")
        Membership.objects.create(user=user, organization=org)
        with pytest.raises(Exception):
            Membership.objects.create(user=user, organization=org)
