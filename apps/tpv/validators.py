"""Validadores de elegibilidade CDA para Transação de Pequeno Valor (TPV).

Referência legal: Edital PGDAU 11/2025.
Elegibilidade: PF, ME, EPP — CDA <= 60 SM — inscrita há > 1 ano.

Módulo puro (sem Django, sem I/O) — apenas Decimal, dataclasses, date.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from apps.tpv.constants import (
    LIMITE_SM_POR_CDA,
    TEMPO_MINIMO_INSCRICAO_DIAS,
    TIPOS_CONTRIBUINTE_ELEGIVEIS,
    calcular_limite_valor_cda,
)


class MotivoInaptidao(Enum):
    """Motivos de inaptidão de uma CDA para TPV.

    Referência: Edital PGDAU 11/2025.
    """

    VALOR_ACIMA_LIMITE = "valor_acima_limite"
    INSCRICAO_INFERIOR_1_ANO = "inscricao_inferior_1_ano"


@dataclass
class CDAValidationResult:
    """Resultado da validação de elegibilidade de uma CDA para TPV.

    Attributes:
        apta: True se a CDA atende todos os critérios.
        motivos: Lista de motivos de inaptidão (vazia se apta).
        data_elegibilidade_tempo: Data em que a CDA se tornará elegível por tempo.
            None se já elegível ou se inapta apenas por valor.
        dias_restantes_tempo: Dias restantes até elegibilidade por tempo.
            0 se já elegível por tempo.
    """

    apta: bool
    motivos: list[MotivoInaptidao] = field(default_factory=list)
    data_elegibilidade_tempo: Optional[date] = None
    dias_restantes_tempo: int = 0


@dataclass
class ElegibilidadeWizardResult:
    """Resultado do wizard simplificado de elegibilidade TPV.

    Attributes:
        elegivel: True se atende todos os critérios.
        criterios: Lista de dicts com status e detalhe de cada critério.
        mensagem: Mensagem resumo da elegibilidade.
    """

    elegivel: bool
    criterios: list[dict] = field(default_factory=list)
    mensagem: str = ""


def validar_cda(
    valor: Decimal,
    data_inscricao: date,
    data_simulacao: date,
    salario_minimo: Decimal,
) -> CDAValidationResult:
    """Valida elegibilidade de uma CDA para Transação de Pequeno Valor.

    Critérios (Edital PGDAU 11/2025):
    1. Valor da CDA <= 60 salários mínimos
    2. CDA inscrita há >= 1 ano (365 dias)

    Args:
        valor: Valor consolidado da CDA em Decimal.
        data_inscricao: Data de inscrição da CDA em dívida ativa.
        data_simulacao: Data da simulação (referência para cálculo de tempo).
        salario_minimo: Valor do salário mínimo vigente.

    Returns:
        CDAValidationResult com aptidão, motivos e projeção de elegibilidade.
    """
    motivos: list[MotivoInaptidao] = []

    # Critério 1: valor <= 60 SM
    limite_valor = calcular_limite_valor_cda(salario_minimo)
    if valor > limite_valor:
        motivos.append(MotivoInaptidao.VALOR_ACIMA_LIMITE)

    # Critério 2: inscrita há >= 365 dias
    dias_inscricao = (data_simulacao - data_inscricao).days
    if dias_inscricao < TEMPO_MINIMO_INSCRICAO_DIAS:
        motivos.append(MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO)

    # Projeção de elegibilidade por tempo
    data_elegibilidade = data_inscricao + timedelta(days=TEMPO_MINIMO_INSCRICAO_DIAS)
    dias_restantes = max(0, (data_elegibilidade - data_simulacao).days)

    apta = len(motivos) == 0

    return CDAValidationResult(
        apta=apta,
        motivos=motivos,
        data_elegibilidade_tempo=data_elegibilidade if dias_restantes > 0 else None,
        dias_restantes_tempo=dias_restantes,
    )


def validar_elegibilidade_wizard(
    tipo_contribuinte: str,
    possui_cda_acima_limite: bool,
    valor_total: Decimal,
    todas_cdas_mais_1_ano: bool,
    salario_minimo: Decimal,
) -> ElegibilidadeWizardResult:
    """Valida elegibilidade TPV via wizard simplificado (checklist).

    Usado no diagnóstico simplificado (HPR PGFN Debt Solve).
    Retorna 3 critérios: tipo contribuinte, limite por CDA, tempo de inscrição.

    Referência: Edital PGDAU 11/2025.

    Args:
        tipo_contribuinte: Tipo do contribuinte ("PF", "ME", "EPP", "PJ", etc.).
        possui_cda_acima_limite: True se possui alguma CDA acima de 60 SM.
        valor_total: Valor total das CDAs em Decimal.
        todas_cdas_mais_1_ano: True se todas as CDAs estão inscritas há > 1 ano.
        salario_minimo: Valor do salário mínimo vigente.

    Returns:
        ElegibilidadeWizardResult com elegibilidade, critérios e mensagem.
    """
    limite_valor = calcular_limite_valor_cda(salario_minimo)
    criterios: list[dict] = []

    # Critério 1: Tipo de contribuinte
    tipo_ok = tipo_contribuinte.upper() in TIPOS_CONTRIBUINTE_ELEGIVEIS
    criterios.append(
        {
            "criterio": "Tipo de Contribuinte",
            "status": "ok" if tipo_ok else "fail",
            "detalhe": (
                f"{tipo_contribuinte} — elegível para TPV"
                if tipo_ok
                else f"{tipo_contribuinte} — apenas PF, ME e EPP são elegíveis"
            ),
        }
    )

    # Critério 2: Limite por CDA (60 SM)
    limite_ok = not possui_cda_acima_limite
    criterios.append(
        {
            "criterio": "Limite por CDA",
            "status": "ok" if limite_ok else "fail",
            "detalhe": (
                f"Todas as CDAs dentro do limite de {LIMITE_SM_POR_CDA} salários mínimos " f"(R$ {limite_valor:,.2f})"
                if limite_ok
                else f"Possui CDA acima de {LIMITE_SM_POR_CDA} salários mínimos "
                f"(R$ {limite_valor:,.2f}) — não elegível"
            ),
        }
    )

    # Critério 3: Tempo de inscrição (> 1 ano)
    tempo_ok = todas_cdas_mais_1_ano
    criterios.append(
        {
            "criterio": "Tempo de Inscrição",
            "status": "ok" if tempo_ok else "fail",
            "detalhe": (
                "Todas as CDAs inscritas há mais de 1 ano"
                if tempo_ok
                else "Possui CDAs inscritas há menos de 1 ano — não elegível"
            ),
        }
    )

    elegivel = tipo_ok and limite_ok and tempo_ok
    mensagem = (
        "Elegível para Transação de Pequeno Valor" if elegivel else "Não elegível para Transação de Pequeno Valor"
    )

    return ElegibilidadeWizardResult(
        elegivel=elegivel,
        criterios=criterios,
        mensagem=mensagem,
    )
