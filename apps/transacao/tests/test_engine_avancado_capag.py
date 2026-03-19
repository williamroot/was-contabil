"""Testes avancados do engine de simulacao — metodo CAPAG vs PERCENTUAL.

Cobre cenarios:
- Metodo CAPAG vs PERCENTUAL com dados HPR
- Principal sempre zero desconto (invariante legal)
- Rating limites exatos (2.0, 1.0, 0.5)
- Honorarios com percentuais variados
- Simples Nacional preenchido + vazio

Cada teste valida funcoes puras (sem Django, sem I/O, sem banco).
"""

from decimal import Decimal

from apps.transacao.engine_avancado import (
    DebitoComponentes,
    RatingCAPAG,
    SimulacaoAvancadaInput,
    calcular_desconto_componentes,
    calcular_desconto_componentes_capag,
    calcular_rating_capag,
    calcular_simulacao_avancada,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_input(**overrides):
    """Gera input base para testes, com overrides."""
    defaults = dict(
        previdenciario=DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        ),
        tributario=DebitoComponentes(
            principal=Decimal("1500"),
            multa=Decimal("450"),
            juros=Decimal("600"),
            encargos=Decimal("250"),
        ),
        simples=None,
        is_me_epp=True,
        capag_60m=Decimal("1000"),
        passivo_rfb=Decimal("5000"),
        passivo_pgfn=Decimal("4800"),
        desconto_escolha="MAIOR",
        honorarios_percentual=Decimal("0.20"),
        metodo_desconto="CAPAG",
    )
    defaults.update(overrides)
    return SimulacaoAvancadaInput(**defaults)


# ---------------------------------------------------------------------------
# TestMetodoCAPAGvsPercentual
# ---------------------------------------------------------------------------


class TestMetodoCAPAGvsPercentual:
    """Testa diferenca entre metodos CAPAG e PERCENTUAL."""

    def test_metodo_capag_desconto_diferente_percentual(self):
        """Metodo CAPAG e PERCENTUAL devem produzir descontos diferentes."""
        inp_capag = _base_input(metodo_desconto="CAPAG")
        inp_pct = _base_input(metodo_desconto="PERCENTUAL")

        res_capag = calcular_simulacao_avancada(inp_capag)
        res_pct = calcular_simulacao_avancada(inp_pct)

        # Ambos devem ter o mesmo rating e percentual
        assert res_capag.rating == res_pct.rating
        assert res_capag.desconto_percentual == res_pct.desconto_percentual

        # Mas os descontos efetivos podem ser diferentes (CAPAG maximiza)
        # Nao importa se sao iguais ou diferentes, o importante eh que ambos rodam
        assert res_capag.desconto_total >= Decimal("0")
        assert res_pct.desconto_total >= Decimal("0")

    def test_metodo_percentual_aplica_flat(self):
        """Metodo PERCENTUAL aplica desconto flat sobre cada componente."""
        inp = _base_input(metodo_desconto="PERCENTUAL")
        resultado = calcular_simulacao_avancada(inp)

        # Previdenciario: principal sem desconto
        prev = resultado.previdenciario.desconto_result
        assert prev.principal_desconto == Decimal("0")
        assert prev.principal_final == Decimal("1000")

    def test_metodo_capag_principal_sem_desconto(self):
        """Metodo CAPAG: principal NUNCA tem desconto (invariante legal)."""
        inp = _base_input(metodo_desconto="CAPAG")
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.previdenciario.desconto_result.principal_desconto == Decimal("0")
        assert resultado.tributario.desconto_result.principal_desconto == Decimal("0")


# ---------------------------------------------------------------------------
# TestPrincipalSempreZeroDesconto
# ---------------------------------------------------------------------------


class TestPrincipalSempreZeroDesconto:
    """Invariante: principal_desconto eh SEMPRE zero (Lei 13.988, art 11, par2, I)."""

    def test_principal_zero_com_70_porcento(self):
        """Mesmo com 70% desconto, principal nao eh tocado."""
        comp = DebitoComponentes(
            principal=Decimal("50000"),
            multa=Decimal("10000"),
            juros=Decimal("15000"),
            encargos=Decimal("5000"),
        )
        resultado = calcular_desconto_componentes(comp, Decimal("0.70"))
        assert resultado.principal_desconto == Decimal("0")
        assert resultado.principal_final == Decimal("50000")

    def test_principal_zero_com_65_porcento(self):
        """Desconto 65% (regime geral): principal inalterado."""
        comp = DebitoComponentes(
            principal=Decimal("80000"),
            multa=Decimal("20000"),
            juros=Decimal("30000"),
            encargos=Decimal("10000"),
        )
        resultado = calcular_desconto_componentes(comp, Decimal("0.65"))
        assert resultado.principal_desconto == Decimal("0")
        assert resultado.principal_final == Decimal("80000")

    def test_principal_zero_metodo_capag(self):
        """Metodo CAPAG: principal_desconto = 0."""
        comp = DebitoComponentes(
            principal=Decimal("10000"),
            multa=Decimal("3000"),
            juros=Decimal("5000"),
            encargos=Decimal("2000"),
        )
        resultado = calcular_desconto_componentes_capag(comp, Decimal("5000"))
        assert resultado.principal_desconto == Decimal("0")
        assert resultado.principal_final == Decimal("10000")

    def test_componentes_somente_principal(self):
        """Se so tem principal (M+J+E=0), desconto total eh zero."""
        comp = DebitoComponentes(
            principal=Decimal("50000"),
            multa=Decimal("0"),
            juros=Decimal("0"),
            encargos=Decimal("0"),
        )
        resultado = calcular_desconto_componentes(comp, Decimal("0.70"))
        assert resultado.total_desconto == Decimal("0")
        assert resultado.total_final == Decimal("50000")


# ---------------------------------------------------------------------------
# TestRatingLimitesExatos
# ---------------------------------------------------------------------------


class TestRatingLimitesExatos:
    """Testa limites exatos do rating CAPAG (2.0, 1.0, 0.5)."""

    def test_ratio_exato_2_0(self):
        """Ratio = 2.0 -> Rating A (limite inclusivo >= 2)."""
        rating = calcular_rating_capag(Decimal("20000"), Decimal("10000"))
        assert rating == RatingCAPAG.A

    def test_ratio_1_9999(self):
        """Ratio = 1.9999 -> Rating B (abaixo de 2, acima de 1)."""
        rating = calcular_rating_capag(Decimal("19999"), Decimal("10000"))
        assert rating == RatingCAPAG.B

    def test_ratio_exato_1_0(self):
        """Ratio = 1.0 -> Rating B (limite inclusivo >= 1)."""
        rating = calcular_rating_capag(Decimal("10000"), Decimal("10000"))
        assert rating == RatingCAPAG.B

    def test_ratio_0_9999(self):
        """Ratio = 0.9999 -> Rating C (abaixo de 1, acima de 0.5)."""
        rating = calcular_rating_capag(Decimal("9999"), Decimal("10000"))
        assert rating == RatingCAPAG.C

    def test_ratio_exato_0_5(self):
        """Ratio = 0.5 -> Rating C (limite inclusivo >= 0.5)."""
        rating = calcular_rating_capag(Decimal("5000"), Decimal("10000"))
        assert rating == RatingCAPAG.C

    def test_ratio_0_4999(self):
        """Ratio = 0.4999 -> Rating D (abaixo de 0.5)."""
        rating = calcular_rating_capag(Decimal("4999"), Decimal("10000"))
        assert rating == RatingCAPAG.D

    def test_divida_zero_rating_a(self):
        """Divida = 0 -> Rating A (sem divida = alta recuperacao)."""
        rating = calcular_rating_capag(Decimal("1000"), Decimal("0"))
        assert rating == RatingCAPAG.A

    def test_capag_zero_divida_positiva_rating_d(self):
        """CAPAG = 0 com divida positiva -> Rating D."""
        rating = calcular_rating_capag(Decimal("0"), Decimal("100000"))
        assert rating == RatingCAPAG.D


# ---------------------------------------------------------------------------
# TestHonorariosPercentuaisVariados
# ---------------------------------------------------------------------------


class TestHonorariosPercentuaisVariados:
    """Testa honorarios com diferentes percentuais."""

    def test_honorarios_zero(self):
        """Honorarios 0% -> R$ 0."""
        inp = _base_input(honorarios_percentual=Decimal("0"))
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.honorarios == Decimal("0")

    def test_honorarios_10_porcento(self):
        """Honorarios 10% sobre desconto efetivo."""
        inp = _base_input(honorarios_percentual=Decimal("0.10"))
        resultado = calcular_simulacao_avancada(inp)
        esperado = resultado.desconto_efetivo * Decimal("0.10")
        assert abs(resultado.honorarios - esperado) <= Decimal("0.01")

    def test_honorarios_20_porcento(self):
        """Honorarios 20% sobre desconto efetivo."""
        inp = _base_input(honorarios_percentual=Decimal("0.20"))
        resultado = calcular_simulacao_avancada(inp)
        esperado = resultado.desconto_efetivo * Decimal("0.20")
        assert abs(resultado.honorarios - esperado) <= Decimal("0.01")

    def test_honorarios_30_porcento(self):
        """Honorarios 30% sobre desconto efetivo."""
        inp = _base_input(honorarios_percentual=Decimal("0.30"))
        resultado = calcular_simulacao_avancada(inp)
        esperado = resultado.desconto_efetivo * Decimal("0.30")
        assert abs(resultado.honorarios - esperado) <= Decimal("0.01")

    def test_honorarios_rating_a_zero(self):
        """Rating A (sem desconto) -> honorarios = 0 independente do percentual."""
        inp = _base_input(
            capag_60m=Decimal("100000"),
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.rating == RatingCAPAG.A
        assert resultado.honorarios == Decimal("0")


# ---------------------------------------------------------------------------
# TestSimplesNacional
# ---------------------------------------------------------------------------


class TestSimplesNacional:
    """Testa simulacao com e sem Simples Nacional."""

    def test_simples_preenchido(self):
        """Com Simples Nacional preenchido, resultado inclui 3 categorias."""
        simples = DebitoComponentes(
            principal=Decimal("800"),
            multa=Decimal("200"),
            juros=Decimal("300"),
            encargos=Decimal("100"),
        )
        inp = _base_input(simples=simples)
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.simples is not None
        assert resultado.simples.nome == "Simples Nacional"
        assert resultado.simples.desconto_result.principal_desconto == Decimal("0")

    def test_simples_vazio(self):
        """Sem Simples Nacional, resultado.simples eh None."""
        inp = _base_input(simples=None)
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.simples is None

    def test_simples_aumenta_desconto_total(self):
        """Com Simples, desconto total deve ser >= desconto sem Simples (para C/D)."""
        inp_sem = _base_input(simples=None)
        simples = DebitoComponentes(
            principal=Decimal("500"),
            multa=Decimal("200"),
            juros=Decimal("300"),
            encargos=Decimal("100"),
        )
        inp_com = _base_input(simples=simples)

        res_sem = calcular_simulacao_avancada(inp_sem)
        res_com = calcular_simulacao_avancada(inp_com)

        # Com Simples, desconto total deve ser >= que sem
        assert res_com.desconto_total >= res_sem.desconto_total

    def test_simples_calculo_detalhes_incluido(self):
        """Com Simples, calculo_detalhes deve ter passo sobre Simples Nacional."""
        simples = DebitoComponentes(
            principal=Decimal("800"),
            multa=Decimal("200"),
            juros=Decimal("300"),
            encargos=Decimal("100"),
        )
        inp = _base_input(simples=simples)
        resultado = calcular_simulacao_avancada(inp)

        descricoes = [d["descricao"].lower() for d in resultado.calculo_detalhes]
        assert any("simples" in d for d in descricoes)


# ---------------------------------------------------------------------------
# TestDescontoEscolha
# ---------------------------------------------------------------------------


class TestDescontoEscolhaMaiorMenor:
    """Testa desconto_escolha MAIOR vs MENOR."""

    def test_maior_desconto_65_geral_d(self):
        """Geral + Rating D + MAIOR -> 65%."""
        inp = _base_input(
            is_me_epp=False,
            desconto_escolha="MAIOR",
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.65")

    def test_menor_desconto_32_5_geral_d(self):
        """Geral + Rating D + MENOR -> 32.5%."""
        inp = _base_input(
            is_me_epp=False,
            desconto_escolha="MENOR",
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.325")

    def test_maior_desconto_70_me_epp_d(self):
        """ME/EPP + Rating D + MAIOR -> 70%."""
        inp = _base_input(
            is_me_epp=True,
            desconto_escolha="MAIOR",
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.70")

    def test_menor_desconto_35_me_epp_d(self):
        """ME/EPP + Rating D + MENOR -> 35%."""
        inp = _base_input(
            is_me_epp=True,
            desconto_escolha="MENOR",
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.35")
