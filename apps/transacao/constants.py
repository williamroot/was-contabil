"""Constantes legais para transação tributária federal (PGFN).

Todas as constantes possuem referência legal (artigo + lei/portaria) conforme
legislação vigente. Valores em Decimal para precisão financeira.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from decimal import Decimal
from enum import Enum

# ---------------------------------------------------------------------------
# Descontos Máximos
# ---------------------------------------------------------------------------

DESCONTO_MAX_GERAL = Decimal("0.65")
"""Desconto máximo de 65% sobre o valor total do crédito.

Aplica-se a contribuintes que não se enquadram como ME, EPP ou pessoa física.
O desconto incide apenas sobre multa, juros e encargos — vedada redução do principal
(art. 11, §2º, I).

References:
    Lei 13.988/2020, art. 11, §2º, II (redação dada pela Lei 14.375/2022).
"""

DESCONTO_MAX_ME_EPP = Decimal("0.70")
"""Desconto máximo de 70% sobre o valor total do crédito para ME/EPP/PF.

Microempresas, empresas de pequeno porte e pessoas físicas têm desconto
ampliado em relação ao regime geral.

References:
    Lei 13.988/2020, art. 11, §3º.
"""

# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

ENTRADA_PERCENTUAL = Decimal("0.06")
"""Percentual de entrada de 6% do valor consolidado, sem descontos.

A entrada é obrigatória e não recebe aplicação de desconto.

References:
    Portaria PGFN 6.757/2022, art. 36.
"""

ENTRADA_PARCELAS_GERAL = 6
"""Número máximo de parcelas para pagamento da entrada (regime geral).

Contribuintes que não se enquadram como ME/EPP/PF pagam a entrada
em até 6 parcelas mensais e sucessivas.

References:
    Portaria PGFN 6.757/2022, art. 36.
"""

ENTRADA_PARCELAS_ME_EPP = 12
"""Número máximo de parcelas para pagamento da entrada (ME/EPP/PF).

Microempresas, empresas de pequeno porte e pessoas físicas pagam a entrada
em até 12 parcelas mensais e sucessivas.

References:
    Portaria PGFN 6.757/2022, art. 36, §2º.
"""

# ---------------------------------------------------------------------------
# Prazos Máximos (em meses)
# ---------------------------------------------------------------------------

PRAZO_MAX_PREVIDENCIARIO = 60
"""Prazo máximo de 60 meses para contribuições previdenciárias.

Limite constitucional aplicável ao parcelamento de contribuições
previdenciárias patronais e dos trabalhadores, independentemente
do regime do contribuinte (geral ou ME/EPP).

References:
    CF/88, art. 195, §11 (com redação da EC 103/2019).
"""

PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL = 120
"""Prazo máximo de 120 meses para débitos não previdenciários (regime geral).

Aplica-se a contribuintes que não se enquadram como ME/EPP/PF.

References:
    Lei 13.988/2020, art. 11, §2º, III.
"""

PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP = 145
"""Prazo máximo de 145 meses para débitos não previdenciários (ME/EPP/PF).

Microempresas, empresas de pequeno porte e pessoas físicas têm prazo
ampliado em relação ao regime geral.

References:
    Lei 13.988/2020, art. 11, §3º.
"""

# ---------------------------------------------------------------------------
# Parcela Mínima
# ---------------------------------------------------------------------------

PARCELA_MINIMA_MEI = Decimal("25")
"""Valor mínimo da parcela mensal para Microempreendedor Individual (MEI): R$ 25,00.

References:
    Portaria PGFN 6.757/2022.
"""

PARCELA_MINIMA_DEMAIS = Decimal("100")
"""Valor mínimo da parcela mensal para os demais contribuintes (exceto MEI): R$ 100,00.

Inclui PJ em geral, ME, EPP e PF.

References:
    Portaria PGFN 6.757/2022.
"""


# ---------------------------------------------------------------------------
# Classificação de Crédito (CAPAG)
# ---------------------------------------------------------------------------


class ClassificacaoCredito(Enum):
    """Classificação de crédito pela Capacidade de Pagamento (CAPAG).

    A PGFN classifica os créditos em 4 níveis com base na relação
    entre a capacidade de pagamento presumida e a dívida consolidada.

    References:
        Portaria PGFN 6.757/2022, arts. 21-25.
    """

    A = "A"
    """Alta recuperação — CAPAG >= 2x dívida consolidada (art. 24)."""

    B = "B"
    """Média recuperação — CAPAG >= 1x dívida, < 2x (art. 24)."""

    C = "C"
    """Difícil recuperação — CAPAG >= 0.5x dívida, < 1x (art. 24)."""

    D = "D"
    """Irrecuperável — CAPAG < 0.5x dívida (art. 24), ou critérios objetivos (art. 25)."""


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------


def get_desconto_por_classificacao(classificacao: ClassificacaoCredito, is_me_epp: bool) -> Decimal:
    """Retorna o percentual máximo de desconto conforme classificação CAPAG.

    Classificações A e B (alta/média recuperação) não têm desconto — apenas
    entrada facilitada. Classificações C e D recebem o desconto máximo
    permitido por lei.

    Args:
        classificacao: Classificação CAPAG do crédito (A, B, C ou D).
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.

    Returns:
        Decimal com o percentual de desconto (0.0 a 0.70). Ex: Decimal("0.65").

    References:
        - Portaria PGFN 6.757/2022, arts. 21-25 (classificação CAPAG).
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% geral).
        - Lei 13.988/2020, art. 11, §3º (limite 70% ME/EPP/PF).
    """
    if classificacao in (ClassificacaoCredito.A, ClassificacaoCredito.B):
        return Decimal("0")

    return DESCONTO_MAX_ME_EPP if is_me_epp else DESCONTO_MAX_GERAL


def get_prazo_parcelas_restantes(is_me_epp: bool, is_previdenciario: bool) -> int:
    """Calcula o número de parcelas restantes após o pagamento da entrada.

    Parcelas restantes = prazo máximo total - parcelas de entrada.

    Args:
        is_me_epp: True se o contribuinte é ME, EPP ou pessoa física.
        is_previdenciario: True se o débito é de natureza previdenciária.

    Returns:
        Número inteiro de parcelas restantes (sempre > 0).

    References:
        - CF/88, art. 195, §11 (limite 60 meses previdenciário).
        - Lei 13.988/2020, art. 11, §2º, III (limite 120 meses geral).
        - Lei 13.988/2020, art. 11, §3º (limite 145 meses ME/EPP).
        - Portaria PGFN 6.757/2022, art. 36 (entrada 6 ou 12 parcelas).
    """
    parcelas_entrada = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL

    if is_previdenciario:
        prazo_total = PRAZO_MAX_PREVIDENCIARIO
    elif is_me_epp:
        prazo_total = PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP
    else:
        prazo_total = PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL

    return prazo_total - parcelas_entrada
