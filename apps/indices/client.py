"""Client HTTP para API BCB SGS (Sistema Gerenciador de Séries Temporais).

Consome séries de índices econômicos do Banco Central do Brasil:
- Série 4390: SELIC acumulada mensal (% a.m.)
- Série 11: SELIC diária (% a.d.)
- Série 433: IPCA mensal (%)

Endpoint: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json

Referências legais:
- Lei 13.988/2020, art. 11, §1º: parcelas atualizadas pela SELIC acumulada
  mensal + 1% no mês do pagamento.
- Fórmula: valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import reduce

import httpx

from django.conf import settings

# Timeout padrão para requisições à API BCB (segundos)
BCB_REQUEST_TIMEOUT = 30

# Códigos das séries BCB SGS utilizadas
SERIE_SELIC_MENSAL = 4390
SERIE_SELIC_DIARIA = 11
SERIE_IPCA_MENSAL = 433


@dataclass(frozen=True)
class IndiceDTO:
    """Índice econômico retornado pela API BCB SGS.

    Attributes:
        data_referencia: Data de referência do índice.
        valor: Valor do índice em Decimal (nunca float).
    """

    data_referencia: date
    valor: Decimal


class BCBClient:
    """Client HTTP síncrono para API BCB SGS.

    Usa httpx sync para consumir séries temporais do Banco Central.
    Todos os valores são convertidos para Decimal para precisão financeira.

    Attributes:
        base_url: URL base da API BCB SGS (de settings.BCB_API_BASE_URL).
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.BCB_API_BASE_URL

    def _parse_response(self, raw: list[dict]) -> list[IndiceDTO]:
        """Converte resposta JSON da API BCB para lista de IndiceDTO.

        A API retorna:
        - data: string no formato DD/MM/YYYY
        - valor: string numérica (pode ser negativa em caso de deflação)

        Args:
            raw: Lista de dicts com chaves 'data' e 'valor'.

        Returns:
            Lista de IndiceDTO com data convertida para date
            e valor convertido para Decimal.
        """
        resultado = []
        for item in raw:
            dia, mes, ano = item["data"].split("/")
            data_referencia = date(int(ano), int(mes), int(dia))
            valor = Decimal(item["valor"])
            resultado.append(IndiceDTO(data_referencia=data_referencia, valor=valor))
        return resultado

    def buscar_serie(
        self,
        codigo: int,
        data_inicial: date,
        data_final: date,
    ) -> list[IndiceDTO]:
        """Busca série temporal por período na API BCB SGS.

        Endpoint:
            {base_url}.{codigo}/dados?formato=json&dataInicial=DD/MM/YYYY&dataFinal=DD/MM/YYYY

        Args:
            codigo: Código da série BCB (ex: 4390 para SELIC mensal).
            data_inicial: Data inicial do período (inclusive).
            data_final: Data final do período (inclusive).

        Returns:
            Lista de IndiceDTO ordenada por data de referência.

        Raises:
            httpx.HTTPStatusError: Se a API retornar erro HTTP.
        """
        dt_inicial = data_inicial.strftime("%d/%m/%Y")
        dt_final = data_final.strftime("%d/%m/%Y")
        url = f"{self.base_url}.{codigo}/dados" f"?formato=json&dataInicial={dt_inicial}&dataFinal={dt_final}"

        response = httpx.get(url, timeout=BCB_REQUEST_TIMEOUT)
        response.raise_for_status()

        return self._parse_response(response.json())

    def buscar_ultimos(self, codigo: int, n: int) -> list[IndiceDTO]:
        """Busca os últimos N registros de uma série na API BCB SGS.

        Endpoint:
            {base_url}.{codigo}/dados/ultimos/{n}?formato=json

        Args:
            codigo: Código da série BCB (ex: 433 para IPCA mensal).
            n: Quantidade de últimos registros a buscar.

        Returns:
            Lista de IndiceDTO com os últimos N registros.

        Raises:
            httpx.HTTPStatusError: Se a API retornar erro HTTP.
        """
        url = f"{self.base_url}.{codigo}/dados/ultimos/{n}?formato=json"

        response = httpx.get(url, timeout=BCB_REQUEST_TIMEOUT)
        response.raise_for_status()

        return self._parse_response(response.json())

    @staticmethod
    def calcular_selic_acumulada(indices: list[IndiceDTO]) -> Decimal:
        """Calcula fator de correção pela SELIC acumulada.

        Lei 13.988/2020, art. 11, §1º:
        fator = Π(1 + taxa_mensal_i / 100) para cada mês i

        O valor corrigido final deve ser calculado como:
        valor_corrigido = valor_original × fator × 1.01 (1% no mês do pagamento)

        Este método retorna apenas o fator acumulado (produtório).
        A multiplicação por 1.01 é responsabilidade do chamador,
        pois depende do contexto (mês de pagamento).

        Args:
            indices: Lista de IndiceDTO com taxas mensais (% a.m.).

        Returns:
            Fator acumulado como Decimal. Retorna Decimal('1') se lista vazia.
        """
        if not indices:
            return Decimal("1")

        return reduce(
            lambda acumulador, indice: acumulador * (Decimal("1") + indice.valor / Decimal("100")),
            indices,
            Decimal("1"),
        )
