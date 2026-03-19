"""Testes do client HTTP para API BCB SGS (SELIC/IPCA).

Referências:
- API BCB SGS: https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros
- Séries: 4390 (SELIC mensal), 11 (SELIC diária), 433 (IPCA mensal)
- Lei 13.988/2020, art. 11, §1º: fórmula SELIC acumulada
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.indices.client import BCBClient, IndiceDTO


class TestIndiceDTO:
    """Testa a dataclass IndiceDTO."""

    def test_cria_indice_dto(self):
        dto = IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.87"))
        assert dto.data_referencia == date(2024, 1, 1)
        assert dto.valor == Decimal("0.87")

    def test_indice_dto_valor_decimal(self):
        """Garante que valor é Decimal, não float."""
        dto = IndiceDTO(data_referencia=date(2024, 6, 15), valor=Decimal("1.05"))
        assert isinstance(dto.valor, Decimal)


class TestBCBClientParseResponse:
    """Testa parsing da resposta JSON da API BCB SGS."""

    def test_parse_response_json(self):
        """Parsear resposta JSON do BCB corretamente.

        API retorna data no formato DD/MM/YYYY e valor como string.
        Deve converter para date e Decimal respectivamente.
        """
        client = BCBClient()
        raw = [
            {"data": "01/01/2024", "valor": "0.87"},
            {"data": "01/02/2024", "valor": "0.79"},
            {"data": "01/03/2024", "valor": "0.83"},
        ]

        resultado = client._parse_response(raw)

        assert len(resultado) == 3
        assert resultado[0].data_referencia == date(2024, 1, 1)
        assert resultado[0].valor == Decimal("0.87")
        assert resultado[1].data_referencia == date(2024, 2, 1)
        assert resultado[1].valor == Decimal("0.79")
        assert resultado[2].data_referencia == date(2024, 3, 1)
        assert resultado[2].valor == Decimal("0.83")

    def test_parse_response_json_valor_negativo(self):
        """Parseia corretamente valores negativos (deflação)."""
        client = BCBClient()
        raw = [{"data": "01/06/2020", "valor": "-0.21"}]

        resultado = client._parse_response(raw)

        assert resultado[0].valor == Decimal("-0.21")

    def test_parse_response_json_vazio(self):
        """Lista vazia retorna lista vazia."""
        client = BCBClient()
        resultado = client._parse_response([])
        assert resultado == []

    def test_parse_response_preserva_precisao_decimal(self):
        """Garante que precisão decimal é mantida (não converte via float)."""
        client = BCBClient()
        raw = [{"data": "15/07/2024", "valor": "0.123456789"}]

        resultado = client._parse_response(raw)

        assert resultado[0].valor == Decimal("0.123456789")
        assert str(resultado[0].valor) == "0.123456789"


class TestBCBClientBuscarSerie:
    """Testa chamadas HTTP para API BCB SGS."""

    @patch("apps.indices.client.httpx")
    def test_buscar_serie_chama_url_correta(self, mock_httpx):
        """Mock httpx: verifica que URL contém código da série e datas formatadas."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"data": "01/01/2024", "valor": "0.87"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        resultado = client.buscar_serie(
            codigo=4390,
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 3, 31),
        )

        mock_httpx.get.assert_called_once()
        url_chamada = mock_httpx.get.call_args[0][0]

        # URL deve conter código da série
        assert "4390" in url_chamada
        # URL deve conter datas no formato DD/MM/YYYY
        assert "01/01/2024" in url_chamada
        assert "31/03/2024" in url_chamada
        # Deve ter formato=json
        assert "formato=json" in url_chamada

        # Resultado deve ser lista de IndiceDTO
        assert len(resultado) == 1
        assert isinstance(resultado[0], IndiceDTO)

    @patch("apps.indices.client.httpx")
    def test_buscar_serie_usa_base_url_do_settings(self, mock_httpx):
        """URL base deve vir de django.conf.settings.BCB_API_BASE_URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        client.buscar_serie(
            codigo=433,
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 12, 31),
        )

        url_chamada = mock_httpx.get.call_args[0][0]
        assert url_chamada.startswith("https://api.bcb.gov.br/dados/serie/bcdata.sgs")

    @patch("apps.indices.client.httpx")
    def test_buscar_serie_chama_raise_for_status(self, mock_httpx):
        """Deve chamar raise_for_status() para propagar erros HTTP."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        client.buscar_serie(
            codigo=11,
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 1, 31),
        )

        mock_response.raise_for_status.assert_called_once()

    @patch("apps.indices.client.httpx")
    def test_buscar_serie_timeout(self, mock_httpx):
        """Deve passar timeout na requisição."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        client.buscar_serie(
            codigo=4390,
            data_inicial=date(2024, 1, 1),
            data_final=date(2024, 1, 31),
        )

        _, kwargs = mock_httpx.get.call_args
        assert "timeout" in kwargs
        assert kwargs["timeout"] > 0


class TestBCBClientBuscarUltimos:
    """Testa busca dos últimos N registros de uma série."""

    @patch("apps.indices.client.httpx")
    def test_buscar_ultimos_url_correta(self, mock_httpx):
        """URL deve conter /dados/ultimos/{n} e formato=json."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"data": "01/01/2024", "valor": "0.87"},
            {"data": "01/02/2024", "valor": "0.79"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        resultado = client.buscar_ultimos(codigo=4390, n=2)

        url_chamada = mock_httpx.get.call_args[0][0]
        assert "4390" in url_chamada
        assert "ultimos/2" in url_chamada
        assert "formato=json" in url_chamada
        assert len(resultado) == 2

    @patch("apps.indices.client.httpx")
    def test_buscar_ultimos_retorna_indice_dto(self, mock_httpx):
        """Resultado deve ser lista de IndiceDTO."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"data": "01/06/2024", "valor": "0.50"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        client = BCBClient()
        resultado = client.buscar_ultimos(codigo=433, n=1)

        assert len(resultado) == 1
        assert isinstance(resultado[0], IndiceDTO)
        assert resultado[0].valor == Decimal("0.50")


class TestCalcularSelicAcumulada:
    """Testa cálculo da SELIC acumulada.

    Lei 13.988/2020, art. 11, §1º:
    fator = Produto de (1 + taxa_mensal/100) para cada mês
    valor_corrigido = valor_original x fator x 1.01 (1% no mês do pagamento)
    """

    def test_calcular_selic_acumulada_basico(self):
        """Produto de (1 + taxa/100) para lista de índices.

        Exemplo: taxas 0.87% e 0.79%
        fator = (1 + 0.0087) × (1 + 0.0079)
              = 1.0087 × 1.0079
              = 1.01666873
        """
        client = BCBClient()
        indices = [
            IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.87")),
            IndiceDTO(data_referencia=date(2024, 2, 1), valor=Decimal("0.79")),
        ]

        resultado = client.calcular_selic_acumulada(indices)

        esperado = (Decimal("1") + Decimal("0.87") / Decimal("100")) * (Decimal("1") + Decimal("0.79") / Decimal("100"))
        assert resultado == esperado

    def test_calcular_selic_acumulada_unico_mes(self):
        """Com apenas um mês, fator = (1 + taxa/100)."""
        client = BCBClient()
        indices = [
            IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.87")),
        ]

        resultado = client.calcular_selic_acumulada(indices)

        assert resultado == Decimal("1") + Decimal("0.87") / Decimal("100")

    def test_calcular_selic_acumulada_lista_vazia(self):
        """Lista vazia deve retornar fator neutro (1)."""
        client = BCBClient()
        resultado = client.calcular_selic_acumulada([])
        assert resultado == Decimal("1")

    def test_calcular_selic_acumulada_12_meses(self):
        """Teste com 12 meses de taxas reais (~SELIC 2024).

        Verifica que resultado é Decimal e maior que 1.
        """
        client = BCBClient()
        taxas_mensais = [
            "0.97",
            "0.80",
            "0.83",
            "0.89",
            "0.83",
            "0.79",
            "0.91",
            "0.87",
            "0.84",
            "0.93",
            "0.79",
            "0.89",
        ]
        indices = [
            IndiceDTO(
                data_referencia=date(2024, mes + 1, 1),
                valor=Decimal(taxa),
            )
            for mes, taxa in enumerate(taxas_mensais)
        ]

        resultado = client.calcular_selic_acumulada(indices)

        assert isinstance(resultado, Decimal)
        assert resultado > Decimal("1")
        # SELIC anual ~10.5% => fator ~1.105
        assert Decimal("1.09") < resultado < Decimal("1.12")

    def test_calcular_selic_acumulada_precisao_decimal(self):
        """Garante que cálculo usa Decimal puro, sem intermediário float."""
        client = BCBClient()
        indices = [
            IndiceDTO(data_referencia=date(2024, 1, 1), valor=Decimal("0.10")),
            IndiceDTO(data_referencia=date(2024, 2, 1), valor=Decimal("0.10")),
            IndiceDTO(data_referencia=date(2024, 3, 1), valor=Decimal("0.10")),
        ]

        resultado = client.calcular_selic_acumulada(indices)

        # (1.001)^3 = 1.003003001 — Decimal exato
        esperado = Decimal("1.001") ** 3
        assert resultado == esperado
