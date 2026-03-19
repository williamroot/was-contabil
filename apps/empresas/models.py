"""Model Empresa — dados cadastrais do cliente do escritório.

Multi-tenant: toda empresa pertence a uma Organization (FK).
Custom Manager com métodos de filtro por org e busca.
"""

from django.db import models

from apps.core.models import Organization, UUIDModel


class EmpresaQuerySet(models.QuerySet):
    """QuerySet customizado com métodos de negócio."""

    def da_organizacao(self, org):
        """Filtra empresas de uma organização específica."""
        return self.filter(organization=org)

    def buscar(self, org, termo):
        """Busca empresas por nome OU CNPJ dentro de uma organização.

        Busca case-insensitive (icontains) em nome e cnpj.
        """
        return self.da_organizacao(org).filter(models.Q(nome__icontains=termo) | models.Q(cnpj__icontains=termo))


class EmpresaManager(models.Manager):
    """Manager customizado que expõe métodos do QuerySet."""

    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db)

    def da_organizacao(self, org):
        """Filtra empresas de uma organização específica."""
        return self.get_queryset().da_organizacao(org)

    def buscar(self, org, termo):
        """Busca empresas por nome ou CNPJ dentro de uma organização."""
        return self.get_queryset().buscar(org, termo)


PORTE_CHOICES = [
    ("ME/EPP", "ME/EPP"),
    ("DEMAIS", "DEMAIS"),
]


class Empresa(UUIDModel):
    """Empresa-cliente cadastrada por um escritório/consultoria.

    Cada empresa pertence a exatamente uma organização (multi-tenant).
    Herda UUID v4 como PK de UUIDModel.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="empresas",
    )
    nome = models.CharField(max_length=300)
    cnpj = models.CharField(max_length=18, verbose_name="CNPJ")
    porte = models.CharField(max_length=20, choices=PORTE_CHOICES)
    honorarios_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Honorários (%)",
    )
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EmpresaManager()

    class Meta:
        unique_together = ["cnpj", "organization"]
        ordering = ["nome"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.nome} ({self.cnpj})"
