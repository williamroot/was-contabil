"""Testes das constantes legais de transação tributária (PGFN).

Cada teste valida uma constante ou função definida em apps/transacao/constants.py,
garantindo conformidade com a legislação vigente.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from decimal import Decimal

import pytest

from apps.transacao.constants import (
    DESCONTO_MAX_GERAL,
    DESCONTO_MAX_ME_EPP,
    ENTRADA_PARCELAS_GERAL,
    ENTRADA_PARCELAS_ME_EPP,
    ENTRADA_PERCENTUAL,
    PARCELA_MINIMA_DEMAIS,
    PARCELA_MINIMA_MEI,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
    ClassificacaoCredito,
    get_desconto_por_classificacao,
    get_prazo_parcelas_restantes,
)


class TestConstantesDesconto:
    """Testa constantes de desconto máximo (Lei 13.988/2020)."""

    def test_desconto_max_geral_65_porcento(self):
        """Lei 13.988/2020, art. 11, §2º, II (redação Lei 14.375/2022)."""
        assert DESCONTO_MAX_GERAL == Decimal("0.65")

    def test_desconto_max_me_epp_70_porcento(self):
        """Lei 13.988/2020, art. 11, §3º."""
        assert DESCONTO_MAX_ME_EPP == Decimal("0.70")

    def test_desconto_geral_menor_que_me_epp(self):
        """ME/EPP sempre tem desconto maior ou igual ao geral."""
        assert DESCONTO_MAX_GERAL < DESCONTO_MAX_ME_EPP


class TestConstantesEntrada:
    """Testa constantes de entrada (Portaria PGFN 6.757/2022, art. 36)."""

    def test_entrada_percentual_6_porcento(self):
        """Portaria PGFN 6.757/2022, art. 36."""
        assert ENTRADA_PERCENTUAL == Decimal("0.06")

    def test_entrada_parcelas_geral_6(self):
        """Portaria PGFN 6.757/2022, art. 36."""
        assert ENTRADA_PARCELAS_GERAL == 6

    def test_entrada_parcelas_me_epp_12(self):
        """Portaria PGFN 6.757/2022, art. 36, §2º."""
        assert ENTRADA_PARCELAS_ME_EPP == 12

    def test_me_epp_tem_mais_parcelas_entrada(self):
        """ME/EPP sempre tem mais parcelas de entrada que o regime geral."""
        assert ENTRADA_PARCELAS_ME_EPP > ENTRADA_PARCELAS_GERAL


class TestConstantesPrazo:
    """Testa constantes de prazo máximo (Lei 13.988/2020, CF/88)."""

    def test_prazo_max_previdenciario_60(self):
        """CF/88, art. 195, §11 (EC 103/2019)."""
        assert PRAZO_MAX_PREVIDENCIARIO == 60

    def test_prazo_max_nao_previdenciario_geral_120(self):
        """Lei 13.988/2020, art. 11, §2º, III."""
        assert PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL == 120

    def test_prazo_max_nao_previdenciario_me_epp_145(self):
        """Lei 13.988/2020, art. 11, §3º."""
        assert PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP == 145

    def test_previdenciario_menor_prazo(self):
        """Previdenciário tem limite constitucional mais restritivo."""
        assert PRAZO_MAX_PREVIDENCIARIO < PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL
        assert PRAZO_MAX_PREVIDENCIARIO < PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP

    def test_me_epp_tem_mais_prazo_nao_previdenciario(self):
        """ME/EPP sempre tem prazo maior que geral para não previdenciário."""
        assert PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP > PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL


class TestConstantesParcelaMinima:
    """Testa constantes de parcela mínima (Portaria PGFN 6.757/2022)."""

    def test_parcela_minima_mei_25(self):
        """Portaria PGFN 6.757/2022."""
        assert PARCELA_MINIMA_MEI == Decimal("25")

    def test_parcela_minima_demais_100(self):
        """Portaria PGFN 6.757/2022."""
        assert PARCELA_MINIMA_DEMAIS == Decimal("100")

    def test_mei_tem_parcela_minima_menor(self):
        """MEI tem tratamento diferenciado com parcela mínima menor."""
        assert PARCELA_MINIMA_MEI < PARCELA_MINIMA_DEMAIS


class TestClassificacaoCredito:
    """Testa enum ClassificacaoCredito (Portaria PGFN 6.757/2022, arts. 21-25)."""

    def test_enum_possui_4_classificacoes(self):
        """CAPAG define exatamente 4 classificações: A, B, C, D."""
        assert len(ClassificacaoCredito) == 4

    def test_classificacao_a(self):
        """A = Alta recuperação (CAPAG >= 2x dívida)."""
        assert ClassificacaoCredito.A.value == "A"

    def test_classificacao_b(self):
        """B = Média recuperação (CAPAG >= 1x dívida, < 2x)."""
        assert ClassificacaoCredito.B.value == "B"

    def test_classificacao_c(self):
        """C = Difícil recuperação (CAPAG >= 0.5x dívida, < 1x)."""
        assert ClassificacaoCredito.C.value == "C"

    def test_classificacao_d(self):
        """D = Irrecuperável (CAPAG < 0.5x dívida)."""
        assert ClassificacaoCredito.D.value == "D"

    def test_classificacao_criada_por_valor_string(self):
        """Deve ser possível criar classificação a partir do valor string."""
        assert ClassificacaoCredito("A") == ClassificacaoCredito.A
        assert ClassificacaoCredito("D") == ClassificacaoCredito.D

    def test_classificacao_invalida_levanta_erro(self):
        """Valor inválido deve levantar ValueError."""
        with pytest.raises(ValueError):
            ClassificacaoCredito("E")


class TestGetDescontoPorClassificacao:
    """Testa get_desconto_por_classificacao (Portaria PGFN 6.757/2022, arts. 21-25).

    Classificações A e B: sem desconto (alta/média recuperação).
    Classificações C e D: desconto máximo permitido por lei.
    """

    def test_classificacao_a_sem_desconto_geral(self):
        """A = alta recuperação, sem desconto."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.A, is_me_epp=False)
        assert resultado == Decimal("0")

    def test_classificacao_a_sem_desconto_me_epp(self):
        """A = alta recuperação, sem desconto mesmo para ME/EPP."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.A, is_me_epp=True)
        assert resultado == Decimal("0")

    def test_classificacao_b_sem_desconto_geral(self):
        """B = média recuperação, sem desconto."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.B, is_me_epp=False)
        assert resultado == Decimal("0")

    def test_classificacao_b_sem_desconto_me_epp(self):
        """B = média recuperação, sem desconto mesmo para ME/EPP."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.B, is_me_epp=True)
        assert resultado == Decimal("0")

    def test_classificacao_c_desconto_geral_65(self):
        """C = difícil recuperação, desconto máximo 65% (geral)."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.C, is_me_epp=False)
        assert resultado == Decimal("0.65")

    def test_classificacao_c_desconto_me_epp_70(self):
        """C = difícil recuperação, desconto máximo 70% (ME/EPP)."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.C, is_me_epp=True)
        assert resultado == Decimal("0.70")

    def test_classificacao_d_desconto_geral_65(self):
        """D = irrecuperável, desconto máximo 65% (geral)."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.D, is_me_epp=False)
        assert resultado == Decimal("0.65")

    def test_classificacao_d_desconto_me_epp_70(self):
        """D = irrecuperável, desconto máximo 70% (ME/EPP)."""
        resultado = get_desconto_por_classificacao(ClassificacaoCredito.D, is_me_epp=True)
        assert resultado == Decimal("0.70")

    def test_retorna_decimal(self):
        """Resultado deve ser sempre Decimal (precisão financeira)."""
        for classificacao in ClassificacaoCredito:
            for is_me_epp in (True, False):
                resultado = get_desconto_por_classificacao(classificacao, is_me_epp=is_me_epp)
                assert isinstance(
                    resultado, Decimal
                ), f"Esperado Decimal para {classificacao.value}, is_me_epp={is_me_epp}"


class TestGetPrazoParcelasRestantes:
    """Testa get_prazo_parcelas_restantes.

    Parcelas restantes = prazo total - parcelas de entrada.
    """

    def test_geral_previdenciario(self):
        """60 meses total - 6 entrada = 54 parcelas restantes."""
        resultado = get_prazo_parcelas_restantes(is_me_epp=False, is_previdenciario=True)
        assert resultado == PRAZO_MAX_PREVIDENCIARIO - ENTRADA_PARCELAS_GERAL
        assert resultado == 54

    def test_geral_nao_previdenciario(self):
        """120 meses total - 6 entrada = 114 parcelas restantes."""
        resultado = get_prazo_parcelas_restantes(is_me_epp=False, is_previdenciario=False)
        assert resultado == PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL - ENTRADA_PARCELAS_GERAL
        assert resultado == 114

    def test_me_epp_previdenciario(self):
        """60 meses total - 12 entrada = 48 parcelas restantes."""
        resultado = get_prazo_parcelas_restantes(is_me_epp=True, is_previdenciario=True)
        assert resultado == PRAZO_MAX_PREVIDENCIARIO - ENTRADA_PARCELAS_ME_EPP
        assert resultado == 48

    def test_me_epp_nao_previdenciario(self):
        """145 meses total - 12 entrada = 133 parcelas restantes."""
        resultado = get_prazo_parcelas_restantes(is_me_epp=True, is_previdenciario=False)
        assert resultado == PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP - ENTRADA_PARCELAS_ME_EPP
        assert resultado == 133

    def test_retorna_inteiro(self):
        """Número de parcelas deve ser sempre inteiro."""
        for is_me_epp in (True, False):
            for is_previdenciario in (True, False):
                resultado = get_prazo_parcelas_restantes(is_me_epp=is_me_epp, is_previdenciario=is_previdenciario)
                assert isinstance(
                    resultado, int
                ), f"Esperado int para is_me_epp={is_me_epp}, is_previdenciario={is_previdenciario}"

    def test_resultado_sempre_positivo(self):
        """Parcelas restantes nunca devem ser negativas."""
        for is_me_epp in (True, False):
            for is_previdenciario in (True, False):
                resultado = get_prazo_parcelas_restantes(is_me_epp=is_me_epp, is_previdenciario=is_previdenciario)
                assert resultado > 0, (
                    f"Parcelas restantes devem ser > 0: is_me_epp={is_me_epp}, "
                    f"is_previdenciario={is_previdenciario}"
                )
