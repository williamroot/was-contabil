"""Management command para sincronizar índices SELIC e IPCA do Banco Central.

Uso:
    python manage.py sync_indices
    python manage.py sync_indices --meses 12

Busca dados da API BCB SGS e persiste localmente para cache.
"""

from datetime import date

from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand

from apps.indices.client import SERIE_IPCA_MENSAL, SERIE_SELIC_MENSAL
from apps.indices.service import IndicesService

MESES_PADRAO = 24


class Command(BaseCommand):
    """Sincroniza índices SELIC e IPCA do Banco Central."""

    help = "Sincroniza índices SELIC e IPCA do Banco Central (últimos N meses)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--meses",
            type=int,
            default=MESES_PADRAO,
            help=f"Quantidade de meses para sincronizar (padrão: {MESES_PADRAO})",
        )

    def handle(self, *args, **options):
        meses = options["meses"]
        hoje = date.today()
        data_inicial = hoje - relativedelta(months=meses)

        service = IndicesService()

        self.stdout.write(f"Sincronizando últimos {meses} meses ({data_inicial} a {hoje})...")

        count_selic = service.sync_serie(
            codigo=SERIE_SELIC_MENSAL,
            nome="SELIC mensal",
            data_inicial=data_inicial,
            data_final=hoje,
        )
        self.stdout.write(self.style.SUCCESS(f"  SELIC mensal (4390): {count_selic} registros"))

        count_ipca = service.sync_serie(
            codigo=SERIE_IPCA_MENSAL,
            nome="IPCA mensal",
            data_inicial=data_inicial,
            data_final=hoje,
        )
        self.stdout.write(self.style.SUCCESS(f"  IPCA mensal (433): {count_ipca} registros"))

        total = count_selic + count_ipca
        self.stdout.write(self.style.SUCCESS(f"Total: {total} registros sincronizados."))
