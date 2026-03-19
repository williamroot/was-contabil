"""Model de simulação TPV — Transação de Pequeno Valor.

Multi-tenant: toda simulação pertence a uma Organization (FK).
Herda de UUIDModel (UUID v4 como PK).

Referência legal: Edital PGDAU 11/2025.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Organization, UUIDModel
from apps.empresas.models import Empresa

TIPO_PORTE_CHOICES = [
    ("PF", "Pessoa Física"),
    ("ME", "Microempresa"),
    ("EPP", "Empresa de Pequeno Porte"),
]


class SimulacaoTPV(UUIDModel):
    """Simulação de Transação de Pequeno Valor.

    Armazena entrada, resultado e detalhes do cálculo para auditoria.

    References:
        - Edital PGDAU 11/2025 (TPV).
        - Lei 13.988/2020, art. 11, §2º, I.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="simulacoes_tpv",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes_tpv",
        help_text="Empresa vinculada (opcional). Se preenchida, nome/cnpj vem da empresa.",
    )
    nome_contribuinte = models.CharField(max_length=300, blank=True, default="")
    cpf_cnpj = models.CharField(max_length=18, blank=True, default="")
    tipo_porte = models.CharField(max_length=5, choices=TIPO_PORTE_CHOICES)
    salario_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    parcelas_entrada = models.PositiveSmallIntegerField()
    parcelas_saldo = models.PositiveSmallIntegerField()
    resultado = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes_tpv_criadas",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Simulação TPV"
        verbose_name_plural = "Simulações TPV"

    def __str__(self):
        nome = self.nome_contribuinte or "Sem nome"
        return f"TPV {nome} ({self.tipo_porte})"
