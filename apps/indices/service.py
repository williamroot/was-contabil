"""Serviço de índices econômicos — cache, sync e correção SELIC.

Orquestra a busca de índices na API BCB (via BCBClient), persistência
local (IndiceEconomico) e cálculos de correção monetária.

Referências legais:
- Lei 13.988/2020, art. 11, §1º: parcelas atualizadas pela SELIC acumulada
  mensal + 1% no mês do pagamento.
- Fórmula: valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01
"""

from datetime import date
from decimal import Decimal
from functools import reduce

from apps.indices.client import SERIE_SELIC_MENSAL, BCBClient
from apps.indices.models import IndiceEconomico

# Juros de 1% no mês do pagamento (Lei 13.988/2020, art. 11, §1º)
JUROS_MES_PAGAMENTO = Decimal("1.01")


class IndicesService:
    """Serviço para sync, cache e cálculos de índices econômicos.

    Recebe client por injeção de dependência para facilitar testes.

    Attributes:
        client: Instância de BCBClient (injetada ou criada por padrão).
    """

    def __init__(self, client: BCBClient | None = None):
        self.client = client or BCBClient()

    def sync_serie(
        self,
        codigo: int,
        nome: str,
        data_inicial: date,
        data_final: date,
    ) -> int:
        """Busca série no BCB e persiste/atualiza no banco local.

        Faz upsert: se o registro (serie_codigo, data_referencia) já existe,
        atualiza o valor; caso contrário, cria novo registro.

        Args:
            codigo: Código da série BCB SGS (ex: 4390 para SELIC mensal).
            nome: Nome descritivo da série (ex: 'SELIC mensal').
            data_inicial: Data inicial do período (inclusive).
            data_final: Data final do período (inclusive).

        Returns:
            Quantidade de registros persistidos/atualizados.
        """
        indices = self.client.buscar_serie(codigo, data_inicial, data_final)

        for indice in indices:
            IndiceEconomico.objects.update_or_create(
                serie_codigo=codigo,
                data_referencia=indice.data_referencia,
                defaults={
                    "serie_nome": nome,
                    "valor": indice.valor,
                },
            )

        return len(indices)

    def get_selic_acumulada(
        self,
        data_inicial: date,
        data_final: date,
    ) -> Decimal:
        """Calcula fator SELIC acumulado a partir dos dados locais.

        Busca registros de SELIC mensal (série 4390) no banco local
        e calcula o produtório: Π(1 + taxa_mensal/100).

        Lei 13.988/2020, art. 11, §1º:
        fator = Π(1 + SELIC_mensal_i / 100) para cada mês i no período.

        Args:
            data_inicial: Data inicial do período (inclusive).
            data_final: Data final do período (inclusive).

        Returns:
            Fator acumulado como Decimal. Retorna Decimal('1') se não há dados.
        """
        indices = IndiceEconomico.objects.filter(
            serie_codigo=SERIE_SELIC_MENSAL,
            data_referencia__gte=data_inicial,
            data_referencia__lte=data_final,
        ).order_by("data_referencia")

        if not indices.exists():
            return Decimal("1")

        return reduce(
            lambda acumulador, indice: acumulador * (Decimal("1") + indice.valor / Decimal("100")),
            indices,
            Decimal("1"),
        )

    def corrigir_valor_por_selic(
        self,
        valor: Decimal,
        data_inicial: date,
        data_final: date,
    ) -> Decimal:
        """Corrige valor monetário pela SELIC acumulada + 1% do mês.

        Lei 13.988/2020, art. 11, §1º:
        valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01

        O fator 1.01 representa 1% de juros no mês do pagamento,
        conforme previsto na legislação.

        Args:
            valor: Valor original a ser corrigido (Decimal).
            data_inicial: Data inicial do período de correção (inclusive).
            data_final: Data final do período de correção (inclusive).

        Returns:
            Valor corrigido como Decimal.
        """
        fator = self.get_selic_acumulada(data_inicial, data_final)
        return valor * fator * JUROS_MES_PAGAMENTO
