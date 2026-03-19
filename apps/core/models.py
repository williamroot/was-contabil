"""Models core do WAS Contábil: Organization, Membership, Invitation.

Todos os models herdam de UUIDModel (pk UUID v4).
Multi-tenant por FK organization_id.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """Model base abstrato com UUID v4 como primary key.

    TODOS os models do projeto DEVEM herdar desta classe.
    Garante PKs não-sequenciais (segurança) e merge-safe.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Organization(UUIDModel):
    """Escritório/consultoria — unidade de isolamento multi-tenant.

    Cada organização agrupa usuários (via Membership) e todos os dados
    de negócio (empresas, simulações, etc.) são filtrados por organization.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(UUIDModel):
    """Vínculo usuário <-> organização.

    Um usuário pode pertencer a múltiplas organizações, mas
    unique_together impede duplicatas no mesmo par (user, organization).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_owner = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["user", "organization"]

    def __str__(self):
        return f"{self.user} @ {self.organization}"


class Invitation(UUIDModel):
    """Convite por email para criar organização ou juntar-se a uma existente.

    Fluxo:
    - Superuser cria convite (is_org_invite=True) -> email enviado ->
      destinatário cria conta + nova organização
    - Dono da org cria convite (organization preenchido) -> email enviado ->
      destinatário cria conta e entra na org existente
    """

    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Se null, destinatário cria nova org. Se preenchido, entra na org existente.",
    )
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_org_invite = models.BooleanField(
        default=False,
        help_text="True = convite para criar nova org (só superuser)",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Convite para {self.email}"

    @property
    def is_expired(self):
        """Retorna True se o convite já expirou."""
        return timezone.now() > self.expires_at

    @property
    def is_accepted(self):
        """Retorna True se o convite já foi aceito."""
        return self.accepted_at is not None
