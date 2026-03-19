"""Jobs django-rq para sincronização de índices econômicos.

Tarefas assíncronas que podem ser enfileiradas no Redis via django-rq
para sincronizar séries do Banco Central periodicamente.
"""

import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django_rq import job

from apps.indices.client import SERIE_IPCA_MENSAL, SERIE_SELIC_MENSAL
from apps.indices.service import IndicesService

logger = logging.getLogger(__name__)

# Período padrão de sincronização: últimos 24 meses
MESES_SYNC_PADRAO = 24


@job("default")
def sync_indices_selic():
    """Sincroniza SELIC mensal (série 4390) dos últimos 24 meses.

    Enfileirada no django-rq para execução assíncrona.
    Pode ser chamada periodicamente via cron ou scheduler.
    """
    hoje = date.today()
    data_inicial = hoje - relativedelta(months=MESES_SYNC_PADRAO)

    service = IndicesService()
    count = service.sync_serie(
        codigo=SERIE_SELIC_MENSAL,
        nome="SELIC mensal",
        data_inicial=data_inicial,
        data_final=hoje,
    )

    logger.info("sync_indices_selic: %d registros sincronizados", count)
    return count


@job("default")
def sync_indices_ipca():
    """Sincroniza IPCA mensal (série 433) dos últimos 24 meses.

    Enfileirada no django-rq para execução assíncrona.
    Pode ser chamada periodicamente via cron ou scheduler.
    """
    hoje = date.today()
    data_inicial = hoje - relativedelta(months=MESES_SYNC_PADRAO)

    service = IndicesService()
    count = service.sync_serie(
        codigo=SERIE_IPCA_MENSAL,
        nome="IPCA mensal",
        data_inicial=data_inicial,
        data_final=hoje,
    )

    logger.info("sync_indices_ipca: %d registros sincronizados", count)
    return count
