"""Testes das tasks de sincronizacao de indices.

Valida que as tasks sync_indices_selic e sync_indices_ipca
rodam sem erro com mock do BCBClient.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.indices.client import IndiceDTO


@pytest.mark.django_db
class TestSyncIndicesTasks:
    """Testa tasks de sincronizacao de indices."""

    @patch("apps.indices.service.BCBClient")
    def test_sync_indices_selic_roda(self, mock_client_cls):
        """sync_indices_selic roda sem erro."""
        from apps.indices.tasks import sync_indices_selic

        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.87")),
        ]
        mock_client_cls.return_value = mock_client

        count = sync_indices_selic()
        assert count == 1

    @patch("apps.indices.service.BCBClient")
    def test_sync_indices_ipca_roda(self, mock_client_cls):
        """sync_indices_ipca roda sem erro."""
        from apps.indices.tasks import sync_indices_ipca

        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.50")),
        ]
        mock_client_cls.return_value = mock_client

        count = sync_indices_ipca()
        assert count == 1

    @patch("apps.indices.service.BCBClient")
    def test_sync_selic_retorna_count(self, mock_client_cls):
        """sync_indices_selic retorna contagem de registros."""
        from apps.indices.tasks import sync_indices_selic

        mock_client = MagicMock()
        mock_client.buscar_serie.return_value = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("0.87")),
            IndiceDTO(data_referencia=date(2026, 2, 1), valor=Decimal("0.82")),
            IndiceDTO(data_referencia=date(2026, 3, 1), valor=Decimal("0.75")),
        ]
        mock_client_cls.return_value = mock_client

        count = sync_indices_selic()
        assert count == 3
