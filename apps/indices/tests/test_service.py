"""Testes do IndicesService — cache, sync e correção SELIC.

TDD: testes escritos ANTES da implementação do service.

Referências legais:
- Lei 13.988/2020, art. 11, §1º: parcelas atualizadas pela SELIC acumulada
  mensal + 1% no mês do pagamento.
- Fórmula: valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.indices.client import SERIE_SELIC_MENSAL, IndiceDTO
from apps.indices.models import IndiceEconomico
from apps.indices.service import IndicesService


@pytest.mark.django_db
class TestSyncSerie:
    """Testa sincronização de série BCB para o banco de dados local."""

    def test_sync_serie_persiste_no_banco(self):
        """sync_serie busca dados do client e persiste IndiceEconomico no DB.

        Deve criar registros no banco com serie_codigo, serie_nome,
        data_referencia e valor corretos.
        """
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.87")),
            IndiceDTO(data_referencia=date(2024, 2, 1), valor=Decimal("0.79")),
            IndiceDTO(data_referencia=date(2024, 3, 1), valor=Decimal("0.83")),
        ]

        service = IndicesService(client=mock_client)
        count = service.sync_serie(
            codigo=SERIE_SELIC_MENSAL,
            nome="SELIC mensal",
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 3, 31),
        )

        assert count == 3
        assert IndiceEconomico.objects.count() == 3

        primeiro = IndiceEconomico.objects.filter(
            serie_codigo=SERIE_SELIC_MENSAL,
            data_referencia=date(2024, 1, 1),
        ).first()
        assert primeiro is not None
        assert primeiro.valor == Decimal("0.87")
        assert primeiro.serie_nome == "SELIC mensal"

        mock_client.buscar_serie.assert_called_once_with(
            SERIE_SELIC_MENSAL,
            date(2024, 1, 1),
            date(2024, 3, 31),
        )

    def test_sync_serie_atualiza_existentes(self):
        """sync_serie deve atualizar valores se registro já existe (upsert).

        Evita duplicatas quando a série já foi sincronizada anteriormente.
        """
        IndiceEconomico.objects.create(
            serie_codigo=SERIE_SELIC_MENSAL,
            serie_nome="SELIC mensal",
            data_referencia=date(2024, 1, 1),
            valor=Decimal("0.50"),
        )

        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.87")),
        ]

        service = IndicesService(client=mock_client)
        count = service.sync_serie(
            codigo=SERIE_SELIC_MENSAL,
            nome="SELIC mensal",
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 1, 31),
        )

        assert count == 1
        assert IndiceEconomico.objects.count() == 1

        atualizado = IndiceEconomico.objects.get(
            serie_codigo=SERIE_SELIC_MENSAL,
            data_referencia=date(2024, 1, 1),
        )
        assert atualizado.valor == Decimal("0.87")

    def test_sync_serie_retorna_zero_sem_dados(self):
        """Se client retorna lista vazia, sync_serie retorna 0."""
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = []

        service = IndicesService(client=mock_client)
        count = service.sync_serie(
            codigo=SERIE_SELIC_MENSAL,
            nome="SELIC mensal",
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 1, 31),
        )

        assert count == 0
        assert IndiceEconomico.objects.count() == 0


@pytest.mark.django_db
class TestGetSelicAcumulada:
    """Testa cálculo da SELIC acumulada a partir dos dados do banco."""

    def _popular_selic(self):
        """Helper: cria registros de SELIC mensal no banco."""
        dados = [
            (date(2024, 1, 1), Decimal("0.87")),
            (date(2024, 2, 1), Decimal("0.79")),
            (date(2024, 3, 1), Decimal("0.83")),
        ]
        for dt, valor in dados:
            IndiceEconomico.objects.create(
                serie_codigo=SERIE_SELIC_MENSAL,
                serie_nome="SELIC mensal",
                data_referencia=dt,
                valor=valor,
            )

    def test_get_selic_acumulada_periodo(self):
        """Retorna fator Decimal acumulado para o período.

        Lei 13.988/2020, art. 11, §1º:
        fator = Π(1 + taxa_mensal/100) para cada mês no período.

        Com taxas 0.87%, 0.79%, 0.83%:
        fator = (1.0087) × (1.0079) × (1.0083) = ~1.02500...
        """
        self._popular_selic()

        service = IndicesService(client=MagicMock())
        fator = service.get_selic_acumulada(
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 3, 31),
        )

        assert isinstance(fator, Decimal)
        assert fator > Decimal("1")

        esperado = (
            (Decimal("1") + Decimal("0.87") / Decimal("100"))
            * (Decimal("1") + Decimal("0.79") / Decimal("100"))
            * (Decimal("1") + Decimal("0.83") / Decimal("100"))
        )
        assert fator == esperado

    def test_get_selic_acumulada_sem_dados_retorna_um(self):
        """Sem dados no período, fator deve ser Decimal('1') (neutro)."""
        service = IndicesService(client=MagicMock())
        fator = service.get_selic_acumulada(
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 3, 31),
        )

        assert fator == Decimal("1")


@pytest.mark.django_db
class TestCorrigirValorPorSelic:
    """Testa correção de valor pela SELIC acumulada.

    Lei 13.988/2020, art. 11, §1º:
    valor_corrigido = valor_original × fator_selic × 1.01
    O 1.01 representa 1% de juros no mês do pagamento.
    """

    def _popular_selic(self):
        """Helper: cria registros de SELIC mensal no banco."""
        dados = [
            (date(2024, 1, 1), Decimal("0.87")),
            (date(2024, 2, 1), Decimal("0.79")),
        ]
        for dt, valor in dados:
            IndiceEconomico.objects.create(
                serie_codigo=SERIE_SELIC_MENSAL,
                serie_nome="SELIC mensal",
                data_referencia=dt,
                valor=valor,
            )

    def test_corrigir_valor_por_selic(self):
        """Multiplica valor × fator_acumulado × 1.01.

        Lei 13.988/2020, art. 11, §1º:
        valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01

        Com valor R$1000, taxas 0.87% e 0.79%:
        fator = (1.0087) × (1.0079) = 1.01666873
        corrigido = 1000 × 1.01666873 × 1.01 = 1026.8354...
        """
        self._popular_selic()

        service = IndicesService(client=MagicMock())
        valor_original = Decimal("1000.00")
        corrigido = service.corrigir_valor_por_selic(
            valor=valor_original,
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 2, 28),
        )

        fator = (Decimal("1") + Decimal("0.87") / Decimal("100")) * (Decimal("1") + Decimal("0.79") / Decimal("100"))
        esperado = valor_original * fator * Decimal("1.01")

        assert isinstance(corrigido, Decimal)
        assert corrigido == esperado

    def test_corrigir_valor_por_selic_sem_dados(self):
        """Sem dados SELIC, retorna valor × 1.01 (só juros do mês).

        Fator neutro (1) × 1.01 = 1.01
        """
        service = IndicesService(client=MagicMock())
        corrigido = service.corrigir_valor_por_selic(
            valor=Decimal("1000.00"),
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 2, 28),
        )

        assert corrigido == Decimal("1000.00") * Decimal("1.01")

    def test_corrigir_valor_por_selic_decimal_rigoroso(self):
        """Todos os valores intermediários devem ser Decimal (nunca float)."""
        self._popular_selic()

        service = IndicesService(client=MagicMock())
        corrigido = service.corrigir_valor_por_selic(
            valor=Decimal("500.00"),
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 2, 28),
        )

        assert isinstance(corrigido, Decimal)
        # Verifica que não houve conversão float (precisão mantida)
        assert "E" not in str(corrigido)
