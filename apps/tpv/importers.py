"""Importador CSV/Excel de CDAs exportadas do Regularize.

Parseia planilhas do Regularize e retorna dataclasses CDAInput.
Erros de linhas individuais nao quebram o parse — sao coletados em lista.

Formatos suportados:
- CSV: colunas numero_cda, valor, data_inscricao (DD/MM/YYYY)
- Excel (.xlsx): detecta colunas por header (busca "cda"/"numero", "valor", "data")
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TextIO


@dataclass
class CDAInput:
    """Dados de entrada de uma CDA importada do Regularize.

    Dataclass simples para transporte de dados entre camadas.
    Sera consumido pelo engine de calculo TPV.
    """

    numero: str
    valor: Decimal
    data_inscricao: date


@dataclass
class CDAParseResult:
    """Resultado do parse de arquivo CSV/Excel de CDAs.

    Attributes:
        cdas: Lista de CDAs parseadas com sucesso.
        erros: Lista de mensagens de erro por linha (ex: "Linha 3: valor invalido").
    """

    cdas: list[CDAInput] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)


def _parse_data_inscricao(valor: object) -> date:
    """Converte valor para date, aceitando string DD/MM/YYYY ou datetime object.

    Args:
        valor: String no formato DD/MM/YYYY ou datetime/date object.

    Returns:
        date object.

    Raises:
        ValueError: Se o formato nao for reconhecido.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        data_str = valor.strip()
        # Tentar DD/MM/YYYY primeiro (padrao brasileiro)
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            pass
        # Fallback: YYYY-MM-DD (ISO)
        try:
            return date.fromisoformat(data_str)
        except ValueError:
            raise ValueError(f"Formato de data nao reconhecido: {data_str!r}")
    raise ValueError(f"Formato de data nao reconhecido: {valor!r}")


def _parse_valor(valor: object) -> Decimal:
    """Converte valor para Decimal, aceitando string, int ou float.

    Args:
        valor: Valor monetario como string, int ou float.

    Returns:
        Decimal com precisao financeira.

    Raises:
        InvalidOperation: Se a string nao for um numero valido.
        ValueError: Se o tipo nao for reconhecido.
    """
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    if isinstance(valor, str):
        valor_str = valor.strip()
        # Formato brasileiro: 1.234,56 -> 1234.56
        if "," in valor_str:
            valor_str = valor_str.replace(".", "").replace(",", ".")
        return Decimal(valor_str)
    raise ValueError(f"Tipo de valor nao reconhecido: {type(valor)}")


def parse_cdas_csv(file: TextIO) -> CDAParseResult:
    """Parseia arquivo CSV de CDAs exportado do Regularize.

    Formato esperado: colunas numero_cda, valor, data_inscricao.
    Data no formato DD/MM/YYYY (padrao brasileiro).

    Erros em linhas individuais sao coletados sem interromper o parse.

    Args:
        file: Arquivo CSV aberto em modo texto (TextIO).

    Returns:
        CDAParseResult com CDAs parseadas e lista de erros.
    """
    result = CDAParseResult()
    reader = csv.DictReader(file)

    for numero_linha, row in enumerate(reader, start=2):
        try:
            numero_raw = row.get("numero") or row.get("numero_cda", "")
            numero = numero_raw.strip()
            valor = _parse_valor(row["valor"])
            data_inscricao = _parse_data_inscricao(row["data_inscricao"])

            result.cdas.append(
                CDAInput(
                    numero=numero,
                    valor=valor,
                    data_inscricao=data_inscricao,
                )
            )
        except (ValueError, InvalidOperation, KeyError) as exc:
            result.erros.append(f"Linha {numero_linha}: {exc}")

    return result


def _detectar_colunas_excel(headers: list[str]) -> dict[str, int]:
    """Detecta indices das colunas por palavras-chave no header.

    Busca:
    - "cda" ou "numero" -> coluna numero_cda
    - "valor" -> coluna valor
    - "data" -> coluna data_inscricao

    Args:
        headers: Lista de strings do header do Excel.

    Returns:
        Dict mapeando nome logico -> indice da coluna.

    Raises:
        ValueError: Se alguma coluna obrigatoria nao for encontrada.
    """
    mapeamento: dict[str, int] = {}
    headers_lower = [str(h).lower().strip() if h else "" for h in headers]

    for idx, header in enumerate(headers_lower):
        if not header:
            continue
        if "cda" in header or "numero" in header:
            mapeamento.setdefault("numero_cda", idx)
        elif "valor" in header:
            mapeamento.setdefault("valor", idx)
        elif "data" in header:
            mapeamento.setdefault("data_inscricao", idx)

    colunas_obrigatorias = {"numero_cda", "valor", "data_inscricao"}
    faltantes = colunas_obrigatorias - mapeamento.keys()
    if faltantes:
        raise ValueError(f"Colunas obrigatorias nao encontradas no header: {faltantes}")

    return mapeamento


def parse_cdas_excel(file_bytes: bytes) -> CDAParseResult:
    """Parseia arquivo Excel (.xlsx) de CDAs exportado do Regularize.

    Detecta colunas por header (busca palavras-chave).
    Aceita datas como string DD/MM/YYYY ou datetime objects nativos do Excel.
    Usa read_only=True para performance com arquivos grandes.

    Erros em linhas individuais sao coletados sem interromper o parse.

    Args:
        file_bytes: Conteudo do arquivo .xlsx em bytes.

    Returns:
        CDAParseResult com CDAs parseadas e lista de erros.
    """
    import openpyxl

    result = CDAParseResult()
    buffer = io.BytesIO(file_bytes)
    wb = openpyxl.load_workbook(buffer, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return result

    headers = list(rows[0])
    mapeamento = _detectar_colunas_excel(headers)

    for numero_linha, row in enumerate(rows[1:], start=2):
        try:
            numero = str(row[mapeamento["numero_cda"]]).strip()
            valor = _parse_valor(row[mapeamento["valor"]])
            data_inscricao = _parse_data_inscricao(row[mapeamento["data_inscricao"]])

            result.cdas.append(
                CDAInput(
                    numero=numero,
                    valor=valor,
                    data_inscricao=data_inscricao,
                )
            )
        except (ValueError, InvalidOperation, KeyError, TypeError, IndexError) as exc:
            result.erros.append(f"Linha {numero_linha}: {exc}")

    return result
