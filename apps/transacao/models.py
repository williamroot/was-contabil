"""Models de simulação de transação tributária (básica e avançada).

Multi-tenant: toda simulação pertence a uma Organization (FK).
Herdam de UUIDModel (UUID v4 como PK).
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Organization, UUIDModel
from apps.empresas.models import Empresa

VERSAO_CALCULO_BASICO = "1.0"
VERSAO_CALCULO_AVANCADO = "1.0"

CLASSIFICACAO_CREDITO_CHOICES = [
    ("A", "A - Alta recuperação"),
    ("B", "B - Média recuperação"),
    ("C", "C - Difícil recuperação"),
    ("D", "D - Irrecuperável"),
]

DESCONTO_ESCOLHA_CHOICES = [
    ("MAIOR", "Maior desconto"),
    ("MENOR", "Menor desconto"),
]


class Simulacao(UUIDModel):
    """Simulação básica de transação tributária (diagnóstico prévio).

    Armazena entrada, resultado e detalhes do cálculo para auditoria.
    Empresa é opcional (simulação rápida sem empresa cadastrada).

    References:
        - Lei 13.988/2020 (transação tributária federal).
        - Portaria PGFN 6.757/2022 (regulamentação).
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="simulacoes",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes",
    )
    razao_social = models.CharField(max_length=300, blank=True, default="")
    cnpj = models.CharField(max_length=18, blank=True, default="")
    valor_total_divida = models.DecimalField(max_digits=15, decimal_places=2)
    percentual_previdenciario = models.DecimalField(max_digits=5, decimal_places=4)
    is_me_epp = models.BooleanField(default=False)
    classificacao_credito = models.CharField(
        max_length=1,
        choices=CLASSIFICACAO_CREDITO_CHOICES,
        default="D",
    )
    resultado = models.JSONField(default=dict)
    calculo_detalhes = models.JSONField(default=dict)
    versao_calculo = models.CharField(max_length=20, default=VERSAO_CALCULO_BASICO)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes_criadas",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Simulação Básica"
        verbose_name_plural = "Simulações Básicas"

    def __str__(self):
        nome = self.razao_social or "Sem nome"
        return f"Simulação {nome} - R$ {self.valor_total_divida}"


class SimulacaoAvancada(UUIDModel):
    """Simulação avançada de transação tributária com decomposição P/M/J/E.

    Inclui rating CAPAG automático, 3 categorias de débito e honorários.
    Empresa é obrigatória (vinculada a empresa cadastrada).

    References:
        - Portaria PGFN 6.757/2022, art. 24 (classificação CAPAG).
        - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal).
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="simulacoes_avancadas",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes_avancadas",
    )
    passivo_rfb = models.DecimalField(max_digits=15, decimal_places=2)
    capag_60m = models.DecimalField(max_digits=15, decimal_places=2)
    desconto_escolha = models.CharField(
        max_length=10,
        choices=DESCONTO_ESCOLHA_CHOICES,
        default="MAIOR",
    )

    # Previdenciário P/M/J/E
    previdenciario_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    previdenciario_multa = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    previdenciario_juros = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    previdenciario_encargos = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Tributário P/M/J/E
    tributario_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tributario_multa = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tributario_juros = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tributario_encargos = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Simples Nacional P/M/J/E
    simples_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    simples_multa = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    simples_juros = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    simples_encargos = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    resultado = models.JSONField(default=dict)
    calculo_detalhes = models.JSONField(default=dict)
    versao_calculo = models.CharField(max_length=20, default=VERSAO_CALCULO_AVANCADO)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulacoes_avancadas_criadas",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Simulação Avançada"
        verbose_name_plural = "Simulações Avançadas"

    def __str__(self):
        empresa_nome = self.empresa.nome if self.empresa else "Sem empresa"
        return f"Simulação Avançada {empresa_nome}"
