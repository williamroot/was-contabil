"""Testes para importadores CSV/Excel de CDAs do Regularize.

TDD: estes testes devem ser escritos ANTES da implementacao.
O importador parseia planilhas exportadas do Regularize e retorna
CDAInput dataclasses + lista de erros por linha.
"""

import io
from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from apps.tpv.importers import (
    CDAInput,
    CDAParseResult,
    _parse_data_inscricao,
    _parse_valor,
    parse_cdas_csv,
    parse_cdas_excel,
)


class TestCSVParser:
    """Testa parse_cdas_csv() com arquivos CSV do Regularize."""

    def test_csv_valido_2_linhas_retorna_2_cdas_0_erros(self):
        """CSV valido com 2 linhas de dados retorna 2 CDAs parseadas, 0 erros."""
        csv_content = (
            "numero_cda,valor,data_inscricao\n" "12345678901,1500.50,01/01/2024\n" "98765432109,97260.00,15/06/2025\n"
        )
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert isinstance(result, CDAParseResult)
        assert len(result.cdas) == 2
        assert len(result.erros) == 0

        cda1 = result.cdas[0]
        assert isinstance(cda1, CDAInput)
        assert cda1.numero == "12345678901"
        assert cda1.valor == Decimal("1500.50")
        assert cda1.data_inscricao == date(2024, 1, 1)

        cda2 = result.cdas[1]
        assert cda2.numero == "98765432109"
        assert cda2.valor == Decimal("97260.00")
        assert cda2.data_inscricao == date(2025, 6, 15)

    def test_csv_com_linha_invalida_retorna_1_cda_1_erro(self):
        """CSV com 1 linha valida e 1 invalida retorna 1 CDA + 1 erro com 'linha 3'."""
        csv_content = (
            "numero_cda,valor,data_inscricao\n" "12345678901,1500.50,01/01/2024\n" "98765432109,invalido,15/06/2025\n"
        )
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert len(result.cdas) == 1
        assert len(result.erros) == 1
        assert "linha 3" in result.erros[0].lower()

    def test_csv_vazio_retorna_0_cdas(self):
        """CSV apenas com header (sem dados) retorna 0 CDAs."""
        csv_content = "numero_cda,valor,data_inscricao\n"
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert len(result.cdas) == 0
        assert len(result.erros) == 0


class TestExcelParser:
    """Testa parse_cdas_excel() com arquivos Excel (.xlsx)."""

    @staticmethod
    def _criar_excel_bytes(linhas: list[list], headers: list[str] | None = None) -> bytes:
        """Helper: cria arquivo .xlsx em memoria e retorna bytes.

        Args:
            linhas: Lista de listas com valores das celulas.
            headers: Nomes das colunas. Se None, usa padrao.
        """
        if headers is None:
            headers = ["numero_cda", "valor", "data_inscricao"]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for linha in linhas:
            ws.append(linha)

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def test_excel_valido_2_linhas_retorna_2_cdas(self):
        """Excel com 2 linhas de dados retorna 2 CDAs parseadas."""
        excel_bytes = self._criar_excel_bytes(
            [
                ["12345678901", "1500.50", "01/01/2024"],
                ["98765432109", "97260.00", "15/06/2025"],
            ]
        )

        result = parse_cdas_excel(excel_bytes)

        assert isinstance(result, CDAParseResult)
        assert len(result.cdas) == 2
        assert len(result.erros) == 0

        cda1 = result.cdas[0]
        assert isinstance(cda1, CDAInput)
        assert cda1.numero == "12345678901"
        assert cda1.valor == Decimal("1500.50")
        assert cda1.data_inscricao == date(2024, 1, 1)

    def test_excel_com_celula_invalida_retorna_1_cda_1_erro(self):
        """Excel com 1 linha valida e 1 invalida retorna 1 CDA + 1 erro."""
        excel_bytes = self._criar_excel_bytes(
            [
                ["12345678901", "1500.50", "01/01/2024"],
                ["98765432109", "invalido", "15/06/2025"],
            ]
        )

        result = parse_cdas_excel(excel_bytes)

        assert len(result.cdas) == 1
        assert len(result.erros) == 1
        assert "linha 3" in result.erros[0].lower()

    def test_excel_com_data_datetime_object_parse_correto(self):
        """Excel com data como datetime object (nao string) deve parsear corretamente.

        O Excel frequentemente armazena datas como datetime objects nativos,
        nao como strings DD/MM/YYYY.
        """
        from datetime import datetime

        excel_bytes = self._criar_excel_bytes(
            [
                ["12345678901", 1500.50, datetime(2024, 1, 1)],
                ["98765432109", 97260, datetime(2025, 6, 15)],
            ]
        )

        result = parse_cdas_excel(excel_bytes)

        assert len(result.cdas) == 2
        assert len(result.erros) == 0

        assert result.cdas[0].data_inscricao == date(2024, 1, 1)
        assert result.cdas[0].valor == Decimal("1500.50")

        assert result.cdas[1].data_inscricao == date(2025, 6, 15)
        assert result.cdas[1].valor == Decimal("97260")


class TestCSVParserComColunaNumero:
    """Testa parse_cdas_csv() com coluna 'numero' (compatibilidade com engine)."""

    def test_csv_com_coluna_numero_funciona(self):
        """CSV com header 'numero' (em vez de 'numero_cda') deve funcionar."""
        csv_content = "numero,valor,data_inscricao\n" "12345678901,1500.50,01/01/2024\n"
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert len(result.cdas) == 1
        assert result.cdas[0].numero == "12345678901"


class TestParseValorFormatoBrasileiro:
    """Testa _parse_valor() com formato monetario brasileiro (Bug 5)."""

    def test_formato_brasileiro_com_milhar_e_decimal(self):
        """1.234,56 deve ser parseado como 1234.56."""
        assert _parse_valor("1.234,56") == Decimal("1234.56")

    def test_formato_brasileiro_sem_milhar(self):
        """1234,56 deve ser parseado como 1234.56."""
        assert _parse_valor("1234,56") == Decimal("1234.56")

    def test_formato_brasileiro_com_multiplos_milhares(self):
        """1.234.567,89 deve ser parseado como 1234567.89."""
        assert _parse_valor("1.234.567,89") == Decimal("1234567.89")

    def test_formato_americano_continua_funcionando(self):
        """1500.50 (sem virgula) continua parseando normalmente."""
        assert _parse_valor("1500.50") == Decimal("1500.50")

    def test_inteiro_string(self):
        """Inteiro como string deve funcionar."""
        assert _parse_valor("50000") == Decimal("50000")

    def test_csv_com_valor_brasileiro(self):
        """CSV com valor no formato brasileiro deve parsear corretamente."""
        csv_content = "numero_cda,valor,data_inscricao\n" '12345678901,"1.500,50",01/01/2024\n'
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert len(result.cdas) == 1
        assert result.cdas[0].valor == Decimal("1500.50")


class TestParseDataISO:
    """Testa _parse_data_inscricao() com formato ISO YYYY-MM-DD (Bug 6)."""

    def test_data_iso_yyyy_mm_dd(self):
        """2024-01-15 deve ser parseado corretamente."""
        assert _parse_data_inscricao("2024-01-15") == date(2024, 1, 15)

    def test_data_brasileira_dd_mm_yyyy(self):
        """15/01/2024 deve continuar funcionando."""
        assert _parse_data_inscricao("15/01/2024") == date(2024, 1, 15)

    def test_data_iso_com_espacos(self):
        """ISO com espacos ao redor deve funcionar."""
        assert _parse_data_inscricao("  2024-06-01  ") == date(2024, 6, 1)

    def test_data_brasileira_com_espacos(self):
        """Data brasileira com espacos ao redor deve funcionar."""
        assert _parse_data_inscricao("  01/06/2024  ") == date(2024, 6, 1)

    def test_data_invalida_levanta_erro(self):
        """Data invalida deve levantar ValueError."""
        with pytest.raises(ValueError, match="nao reconhecido"):
            _parse_data_inscricao("data-invalida")

    def test_date_object_retorna_sem_conversao(self):
        """date object deve retornar direto."""
        d = date(2024, 1, 15)
        assert _parse_data_inscricao(d) == d

    def test_csv_com_data_iso(self):
        """CSV com data ISO deve parsear corretamente."""
        csv_content = "numero_cda,valor,data_inscricao\n" "12345678901,1500.50,2024-01-15\n"
        arquivo = io.StringIO(csv_content)

        result = parse_cdas_csv(arquivo)

        assert len(result.cdas) == 1
        assert result.cdas[0].data_inscricao == date(2024, 1, 15)
