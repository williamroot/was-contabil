"""Testes do management command sync_indices.

Valida que o comando roda sem erro e sincroniza indices SELIC e IPCA.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.core.management import call_command

from apps.indices.client import IndiceDTO
from apps.indices.models import IndiceEconomico


@pytest.mark.django_db
class TestSyncIndicesCommand:
    """Testa management command sync_indices."""

    @patch("apps.indices.service.BCBClient")
    def test_command_roda_sem_erro(self, mock_client_cls):
        """sync_indices roda sem erro com mock do BCBClient."""
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.87")),
            IndiceDTO(data_referencia=date(2026, 2, 1), valor=Decimal("0.82")),
        ]
        mock_client_cls.return_value = mock_client

        call_command("sync_indices")

    @patch("apps.indices.service.BCBClient")
    def test_command_persiste_registros(self, mock_client_cls):
        """sync_indices persiste registros no banco."""
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.87")),
        ]
        mock_client_cls.return_value = mock_client

        call_command("sync_indices")

        # Deve ter criado registros para SELIC e IPCA
        assert IndiceEconomico.objects.exists()

    @patch("apps.indices.service.BCBClient")
    def test_command_com_meses_customizado(self, mock_client_cls):
        """sync_indices aceita --meses como parametro."""
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = []
        mock_client_cls.return_value = mock_client

        call_command("sync_indices", "--meses", "6")

    @patch("apps.indices.service.BCBClient")
    def test_command_upsert_nao_duplica(self, mock_client_cls):
        """sync_indices faz upsert (update_or_create), nao duplica registros."""
        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.87")),
        ]
        mock_client_cls.return_value = mock_client

        # Rodar 2 vezes
        call_command("sync_indices")
        call_command("sync_indices")

        # Nao deve ter duplicado (update_or_create)
        count = IndiceEconomico.objects.filter(
            serie_codigo=4390,
            data_referencia=date(2026, 1, 1),
        ).count()
        assert count == 1
