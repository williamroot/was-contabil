"""Models do app indices: índices econômicos do Banco Central.

Armazena séries temporais (SELIC, IPCA) localmente para cache e
cálculos de correção monetária sem depender da API BCB a cada request.
"""

from django.db import models

from apps.core.models import UUIDModel


class IndiceEconomico(UUIDModel):
    """Índice econômico de uma série BCB SGS em uma data de referência.

    Cada registro representa um ponto da série temporal, por exemplo:
    - Série 4390 (SELIC mensal): taxa SELIC acumulada no mês (% a.m.)
    - Série 433 (IPCA mensal): variação do IPCA no mês (%)

    Valores armazenados como Decimal(12, 6) para precisão financeira.

    Referências:
    - API BCB SGS: https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros
    - Lei 13.988/2020, art. 11, §1º: correção pela SELIC acumulada
    """

    serie_codigo = models.IntegerField(
        db_index=True,
        help_text="Código da série BCB SGS (ex: 4390=SELIC mensal, 433=IPCA)",
    )
    serie_nome = models.CharField(
        max_length=100,
        help_text="Nome descritivo da série (ex: 'SELIC mensal')",
    )
    data_referencia = models.DateField(
        db_index=True,
        help_text="Data de referência do índice",
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        help_text="Valor do índice (ex: 0.870000 para 0.87%)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["serie_codigo", "data_referencia"]
        ordering = ["serie_codigo", "data_referencia"]
        verbose_name = "Índice Econômico"
        verbose_name_plural = "Índices Econômicos"

    def __str__(self):
        return f"{self.serie_nome} {self.data_referencia} = {self.valor}"
