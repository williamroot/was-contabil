"""Testes do engine avançado de simulação de transação tributária (PGFN).

TDD rigoroso — testes escritos ANTES da implementação do engine avançado.
Engine com decomposição Principal/Multa/Juros/Encargos, CAPAG rating automático,
3 categorias de débitos (previdenciário, tributário, simples nacional) e honorários.

Cada teste valida uma função pura (sem Django, sem I/O, sem banco).
Todos os valores financeiros em Decimal com ROUND_HALF_UP.

References:
    - Lei 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
    - Portaria PGFN 6.757/2022, art. 24 (classificação CAPAG)
    - Lei 13.988/2020, art. 11, §2º, I (vedação desconto sobre principal)
    - CF/88, art. 195, §11 (EC 103/2019)
"""

from decimal import Decimal

import pytest

from apps.transacao.engine_avancado import (
    CategoriaResult,
    DebitoComponentes,
    DescontoResult,
    RatingCAPAG,
    SimulacaoAvancadaInput,
    SimulacaoAvancadaResult,
    calcular_desconto_componentes,
    calcular_rating_capag,
    calcular_simulacao_avancada,
)

# ---------------------------------------------------------------------------
# TestRatingCAPAG — Portaria PGFN 6.757/2022, art. 24
# ---------------------------------------------------------------------------


class TestRatingCAPAG:
    """Testa calcular_rating_capag(capag, divida).

    Fórmula oficial da Portaria PGFN 6.757/2022, art. 24:
    - CAPAG >= 2x dívida → Rating A
    - CAPAG >= 1x dívida (< 2x) → Rating B
    - CAPAG >= 0.5x dívida (< 1x) → Rating C
    - CAPAG < 0.5x dívida → Rating D
    """

    def test_capag_2x_divida_rating_a(self):
        """CAPAG >= 2x dívida → Rating A (alta recuperação)."""
        rating = calcular_rating_capag(
            capag=Decimal("20000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.A

    def test_capag_3x_divida_rating_a(self):
        """CAPAG 3x dívida → Rating A (muito acima do limite)."""
        rating = calcular_rating_capag(
            capag=Decimal("30000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.A

    def test_capag_1x_divida_rating_b(self):
        """CAPAG >= 1x dívida (< 2x) → Rating B (média recuperação)."""
        rating = calcular_rating_capag(
            capag=Decimal("10000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.B

    def test_capag_1_5x_divida_rating_b(self):
        """CAPAG 1.5x dívida → Rating B."""
        rating = calcular_rating_capag(
            capag=Decimal("15000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.B

    def test_capag_0_5x_divida_rating_c(self):
        """CAPAG >= 0.5x dívida (< 1x) → Rating C (difícil recuperação)."""
        rating = calcular_rating_capag(
            capag=Decimal("5000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.C

    def test_capag_0_7x_divida_rating_c(self):
        """CAPAG 0.7x dívida → Rating C."""
        rating = calcular_rating_capag(
            capag=Decimal("7000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.C

    def test_capag_menor_0_5x_divida_rating_d(self):
        """CAPAG < 0.5x dívida → Rating D (irrecuperável)."""
        rating = calcular_rating_capag(
            capag=Decimal("4000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.D

    def test_caso_sitio_verde_real(self):
        """Caso real Sítio Verde: CAPAG 1000 / Passivo 9800 = 0.102 → D.

        Ratio = 1000 / 9800 = 0.10204... < 0.5 → Rating D.
        """
        rating = calcular_rating_capag(
            capag=Decimal("1000"),
            divida=Decimal("9800"),
        )
        assert rating == RatingCAPAG.D

    def test_divida_zero_rating_a(self):
        """Dívida = 0 → Rating A (sem dívida, máxima recuperação)."""
        rating = calcular_rating_capag(
            capag=Decimal("1000"),
            divida=Decimal("0"),
        )
        assert rating == RatingCAPAG.A

    def test_capag_zero_rating_d(self):
        """CAPAG = 0 → Rating D (sem capacidade de pagamento)."""
        rating = calcular_rating_capag(
            capag=Decimal("0"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.D

    def test_limite_exato_ratio_2_0_rating_a(self):
        """Ratio exatamente 2.0 → Rating A (limite incluso)."""
        rating = calcular_rating_capag(
            capag=Decimal("20000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.A

    def test_limite_exato_ratio_1_0_rating_b(self):
        """Ratio exatamente 1.0 → Rating B (limite incluso)."""
        rating = calcular_rating_capag(
            capag=Decimal("10000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.B

    def test_limite_exato_ratio_0_5_rating_c(self):
        """Ratio exatamente 0.5 → Rating C (limite incluso)."""
        rating = calcular_rating_capag(
            capag=Decimal("5000"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.C

    def test_limite_ratio_0_49_rating_d(self):
        """Ratio 0.49 → Rating D (abaixo do limite de C)."""
        rating = calcular_rating_capag(
            capag=Decimal("4900"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.D

    def test_ambos_zero_rating_a(self):
        """CAPAG = 0, dívida = 0 → Rating A (sem dívida)."""
        rating = calcular_rating_capag(
            capag=Decimal("0"),
            divida=Decimal("0"),
        )
        assert rating == RatingCAPAG.A

    def test_retorna_rating_capag_enum(self):
        """Resultado deve ser sempre RatingCAPAG enum."""
        rating = calcular_rating_capag(
            capag=Decimal("10000"),
            divida=Decimal("10000"),
        )
        assert isinstance(rating, RatingCAPAG)

    def test_limite_logo_abaixo_2_0_rating_b(self):
        """Ratio 1.999... → Rating B (logo abaixo do limite A)."""
        rating = calcular_rating_capag(
            capag=Decimal("19999"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.B

    def test_limite_logo_abaixo_1_0_rating_c(self):
        """Ratio 0.999... → Rating C (logo abaixo do limite B)."""
        rating = calcular_rating_capag(
            capag=Decimal("9999"),
            divida=Decimal("10000"),
        )
        assert rating == RatingCAPAG.C


# ---------------------------------------------------------------------------
# TestDescontoComponentes — Lei 13.988/2020, art. 11, §2º, I
# ---------------------------------------------------------------------------


class TestDescontoComponentes:
    """Testa calcular_desconto_componentes(componentes, desconto_pct).

    REGRA CRÍTICA: Principal NUNCA tem desconto (art. 11, §2º, I).
    Desconto incide apenas sobre multa, juros e encargos.
    """

    def test_principal_nunca_tem_desconto(self):
        """Principal R$1000 com 70% desconto → principal_final=1000, principal_desconto=0.

        Lei 13.988/2020, art. 11, §2º, I: vedada a redução do montante principal.
        """
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert resultado.principal_final == Decimal("1000")
        assert resultado.principal_desconto == Decimal("0")

    def test_multa_com_desconto_70_porcento(self):
        """Multa R$300 com 70% → multa_desconto=210, multa_final=90."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert resultado.multa_desconto == Decimal("210")
        assert resultado.multa_final == Decimal("90")

    def test_juros_com_desconto_70_porcento(self):
        """Juros R$500 com 70% → juros_desconto=350, juros_final=150."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert resultado.juros_desconto == Decimal("350")
        assert resultado.juros_final == Decimal("150")

    def test_encargos_com_desconto_70_porcento(self):
        """Encargos R$200 com 70% → encargos_desconto=140, encargos_final=60."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert resultado.encargos_desconto == Decimal("140")
        assert resultado.encargos_final == Decimal("60")

    def test_total_desconto_soma_componentes(self):
        """total_desconto = multa_desconto + juros_desconto + encargos_desconto."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        # 210 + 350 + 140 = 700
        assert resultado.total_desconto == Decimal("700")

    def test_total_final_com_desconto(self):
        """total_final = principal + componentes restantes após desconto."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        # 1000 + 90 + 150 + 60 = 1300
        assert resultado.total_final == Decimal("1300")

    def test_desconto_zero_rating_a_b(self):
        """Desconto 0% (Rating A/B) → total_desconto=0, total_final=total original."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0"))

        assert resultado.total_desconto == Decimal("0")
        assert resultado.total_final == Decimal("2000")  # 1000+300+500+200
        assert resultado.principal_final == Decimal("1000")
        assert resultado.multa_final == Decimal("300")
        assert resultado.juros_final == Decimal("500")
        assert resultado.encargos_final == Decimal("200")

    def test_desconto_65_porcento_pj_grande_porte_d(self):
        """PJ grande porte com rating D → desconto 65%."""
        componentes = DebitoComponentes(
            principal=Decimal("5000"),
            multa=Decimal("1500"),
            juros=Decimal("2000"),
            encargos=Decimal("500"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.65"))

        assert resultado.principal_final == Decimal("5000")
        assert resultado.principal_desconto == Decimal("0")
        assert resultado.multa_desconto == Decimal("975")  # 1500 * 0.65
        assert resultado.juros_desconto == Decimal("1300")  # 2000 * 0.65
        assert resultado.encargos_desconto == Decimal("325")  # 500 * 0.65
        assert resultado.total_desconto == Decimal("2600")  # 975+1300+325

    def test_principal_50000_com_70_porcento(self):
        """Principal R$50000 com 70% → principal_final=50000, principal_desconto=0."""
        componentes = DebitoComponentes(
            principal=Decimal("50000"),
            multa=Decimal("10000"),
            juros=Decimal("15000"),
            encargos=Decimal("5000"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert resultado.principal_final == Decimal("50000")
        assert resultado.principal_desconto == Decimal("0")

    def test_retorna_desconto_result(self):
        """Resultado deve ser DescontoResult dataclass."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        resultado = calcular_desconto_componentes(componentes, Decimal("0.70"))

        assert isinstance(resultado, DescontoResult)
        assert hasattr(resultado, "__dataclass_fields__")


# ---------------------------------------------------------------------------
# TestDebitoComponentes — properties
# ---------------------------------------------------------------------------


class TestDebitoComponentes:
    """Testa DebitoComponentes dataclass e suas properties."""

    def test_total_soma_componentes(self):
        """total = principal + multa + juros + encargos."""
        comp = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        assert comp.total == Decimal("2000")

    def test_descontavel_exclui_principal(self):
        """descontavel = multa + juros + encargos (sem principal)."""
        comp = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        assert comp.descontavel == Decimal("1000")

    def test_componentes_zerados(self):
        """Componentes zerados: total=0, descontavel=0."""
        comp = DebitoComponentes(
            principal=Decimal("0"),
            multa=Decimal("0"),
            juros=Decimal("0"),
            encargos=Decimal("0"),
        )
        assert comp.total == Decimal("0")
        assert comp.descontavel == Decimal("0")

    def test_somente_principal(self):
        """Somente principal: total=principal, descontavel=0."""
        comp = DebitoComponentes(
            principal=Decimal("5000"),
            multa=Decimal("0"),
            juros=Decimal("0"),
            encargos=Decimal("0"),
        )
        assert comp.total == Decimal("5000")
        assert comp.descontavel == Decimal("0")

    def test_eh_dataclass(self):
        """DebitoComponentes deve ser dataclass."""
        comp = DebitoComponentes(
            principal=Decimal("1000"),
            multa=Decimal("300"),
            juros=Decimal("500"),
            encargos=Decimal("200"),
        )
        assert hasattr(comp, "__dataclass_fields__")


# ---------------------------------------------------------------------------
# TestSimulacaoAvancada — dados HPR plataforma 4 (Sítio Verde)
# ---------------------------------------------------------------------------


class TestSimulacaoAvancada:
    """Testa calcular_simulacao_avancada com dados reais do Sítio Verde.

    Cenário: ME/EPP, CAPAG R$1000, Passivo RFB R$5000,
    Previdenciário P=1000/M=300/J=500/E=200, Tributário P=1500/M=450/J=600/E=250,
    Passivo PGFN R$4800, desconto "MAIOR" (70% ME/EPP), honorários 20%.
    """

    @pytest.fixture
    def input_sitio_verde(self):
        """Input padrão baseado nos dados do Sítio Verde."""
        return SimulacaoAvancadaInput(
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
        )

    def test_rating_d_sitio_verde(self, input_sitio_verde):
        """Rating D: CAPAG 1000, passivo total 9800 (RFB 5000 + PGFN 4800).

        Ratio = 1000 / 9800 = 0.102 → D.
        """
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.rating == RatingCAPAG.D

    def test_desconto_70_porcento_me_epp(self, input_sitio_verde):
        """ME/EPP com rating D + escolha MAIOR → 70%."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.desconto_percentual == Decimal("0.70")

    def test_desconto_total_positivo(self, input_sitio_verde):
        """Desconto total deve ser > 0 para rating D."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.desconto_total > Decimal("0")

    def test_desconto_efetivo_sobre_pgfn(self, input_sitio_verde):
        """Desconto efetivo é limitado ao passivo PGFN.

        desconto_efetivo = min(desconto_total, passivo_pgfn).
        """
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.desconto_efetivo <= resultado.passivos["pgfn"]
        assert resultado.desconto_efetivo <= resultado.desconto_total

    def test_saldo_igual_pgfn_menos_desconto(self, input_sitio_verde):
        """Saldo = passivo PGFN - desconto efetivo."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        saldo_esperado = resultado.passivos["pgfn"] - resultado.desconto_efetivo
        assert resultado.passivos["saldo"] == saldo_esperado

    def test_previdenciario_prazo_60m(self, input_sitio_verde):
        """Previdenciário: prazo total 60 meses (limite constitucional)."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.previdenciario.prazo_total == 60

    def test_previdenciario_entrada_12x(self, input_sitio_verde):
        """ME/EPP: entrada em 12 parcelas."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.previdenciario.entrada == 12

    def test_tributario_prazo_145m(self, input_sitio_verde):
        """Tributário ME/EPP: prazo total 145 meses."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.tributario.prazo_total == 145

    def test_tributario_entrada_12x(self, input_sitio_verde):
        """ME/EPP: entrada em 12 parcelas."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.tributario.entrada == 12

    def test_honorarios_20_porcento_desconto(self, input_sitio_verde):
        """Honorários = desconto_efetivo x 20%."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        honorarios_esperado = resultado.desconto_efetivo * Decimal("0.20")
        # Comparar arredondado
        assert abs(resultado.honorarios - honorarios_esperado) <= Decimal("0.01")

    def test_passivos_dict_completo(self, input_sitio_verde):
        """Passivos deve ter rfb, pgfn, total, saldo."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert "rfb" in resultado.passivos
        assert "pgfn" in resultado.passivos
        assert "total" in resultado.passivos
        assert "saldo" in resultado.passivos

    def test_passivo_total_rfb_mais_pgfn(self, input_sitio_verde):
        """passivo total = rfb + pgfn."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.passivos["total"] == Decimal("5000") + Decimal("4800")

    def test_resultado_eh_dataclass(self, input_sitio_verde):
        """SimulacaoAvancadaResult deve ser dataclass."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert isinstance(resultado, SimulacaoAvancadaResult)
        assert hasattr(resultado, "__dataclass_fields__")

    def test_categoria_previdenciario_tem_componentes(self, input_sitio_verde):
        """CategoriaResult previdenciário deve ter componentes e desconto_result."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.previdenciario.componentes is not None
        assert resultado.previdenciario.desconto_result is not None

    def test_categoria_tributario_tem_componentes(self, input_sitio_verde):
        """CategoriaResult tributário deve ter componentes e desconto_result."""
        resultado = calcular_simulacao_avancada(input_sitio_verde)
        assert resultado.tributario.componentes is not None
        assert resultado.tributario.desconto_result is not None


# ---------------------------------------------------------------------------
# TestRatingABSemDesconto
# ---------------------------------------------------------------------------


class TestRatingABSemDesconto:
    """Testa que ratings A e B não recebem desconto."""

    def test_capag_alta_rating_a_desconto_zero(self):
        """CAPAG alta → Rating A → desconto_total=0, saldo=passivo_pgfn."""
        inp = SimulacaoAvancadaInput(
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
            capag_60m=Decimal("100000"),  # CAPAG muito alta
            passivo_rfb=Decimal("5000"),
            passivo_pgfn=Decimal("4800"),
            desconto_escolha="MAIOR",
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.rating == RatingCAPAG.A
        assert resultado.desconto_total == Decimal("0")
        assert resultado.desconto_efetivo == Decimal("0")
        assert resultado.passivos["saldo"] == Decimal("4800")
        assert resultado.honorarios == Decimal("0")

    def test_capag_media_rating_b_desconto_zero(self):
        """CAPAG média → Rating B → desconto_total=0."""
        inp = SimulacaoAvancadaInput(
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
            is_me_epp=False,
            capag_60m=Decimal("15000"),  # 15000 / 9800 = 1.53 → B
            passivo_rfb=Decimal("5000"),
            passivo_pgfn=Decimal("4800"),
            desconto_escolha="MAIOR",
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.rating == RatingCAPAG.B
        assert resultado.desconto_total == Decimal("0")
        assert resultado.desconto_efetivo == Decimal("0")
        assert resultado.passivos["saldo"] == Decimal("4800")


# ---------------------------------------------------------------------------
# TestCalculoDetalhes
# ---------------------------------------------------------------------------


class TestCalculoDetalhes:
    """Testa que o resultado inclui calculo_detalhes com passos e referências legais."""

    @pytest.fixture
    def resultado_com_detalhes(self):
        """Resultado padrão para teste de detalhes."""
        inp = SimulacaoAvancadaInput(
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
        )
        return calcular_simulacao_avancada(inp)

    def test_calculo_detalhes_presente(self, resultado_com_detalhes):
        """Resultado deve incluir calculo_detalhes."""
        assert resultado_com_detalhes.calculo_detalhes is not None
        assert len(resultado_com_detalhes.calculo_detalhes) > 0

    def test_calculo_detalhes_passos_sequenciais(self, resultado_com_detalhes):
        """Passos devem ser sequenciais (1, 2, 3...)."""
        passos = [d["passo"] for d in resultado_com_detalhes.calculo_detalhes]
        assert passos == list(range(1, len(passos) + 1))

    def test_calculo_detalhes_cada_passo_tem_referencia_legal(self, resultado_com_detalhes):
        """Cada passo deve ter referência legal não vazia."""
        for detalhe in resultado_com_detalhes.calculo_detalhes:
            assert "referencia_legal" in detalhe, f"Passo {detalhe['passo']} sem chave referencia_legal"
            assert detalhe["referencia_legal"].strip() != "", f"Passo {detalhe['passo']} com referência legal vazia"

    def test_calculo_detalhes_cada_passo_tem_descricao(self, resultado_com_detalhes):
        """Cada passo deve ter descrição."""
        for detalhe in resultado_com_detalhes.calculo_detalhes:
            assert "descricao" in detalhe, f"Passo {detalhe['passo']} sem chave descricao"
            assert detalhe["descricao"].strip() != "", f"Passo {detalhe['passo']} com descrição vazia"

    def test_calculo_detalhes_cada_passo_tem_formula(self, resultado_com_detalhes):
        """Cada passo deve ter fórmula descritiva."""
        for detalhe in resultado_com_detalhes.calculo_detalhes:
            assert "formula" in detalhe, f"Passo {detalhe['passo']} sem chave formula"
            assert detalhe["formula"].strip() != "", f"Passo {detalhe['passo']} com fórmula vazia"

    def test_calculo_detalhes_passo_rating_presente(self, resultado_com_detalhes):
        """Deve existir um passo sobre cálculo do rating CAPAG."""
        descricoes = [d["descricao"].lower() for d in resultado_com_detalhes.calculo_detalhes]
        assert any(
            "rating" in desc or "capag" in desc for desc in descricoes
        ), "Nenhum passo sobre Rating CAPAG encontrado nos detalhes"

    def test_calculo_detalhes_passo_desconto_presente(self, resultado_com_detalhes):
        """Deve existir um passo sobre cálculo do desconto."""
        descricoes = [d["descricao"].lower() for d in resultado_com_detalhes.calculo_detalhes]
        assert any("desconto" in desc for desc in descricoes), "Nenhum passo sobre desconto encontrado nos detalhes"


# ---------------------------------------------------------------------------
# TestDescontoEscolhaMenor
# ---------------------------------------------------------------------------


class TestDescontoEscolhaMenor:
    """Testa desconto_escolha='MENOR' (metade do máximo)."""

    def test_menor_desconto_me_epp_35_porcento(self):
        """ME/EPP com escolha MENOR → 35% (metade de 70%)."""
        inp = SimulacaoAvancadaInput(
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
            desconto_escolha="MENOR",
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.35")

    def test_menor_desconto_geral_32_5_porcento(self):
        """Geral com escolha MENOR → 32.5% (metade de 65%)."""
        inp = SimulacaoAvancadaInput(
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
            is_me_epp=False,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            passivo_pgfn=Decimal("4800"),
            desconto_escolha="MENOR",
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)
        assert resultado.desconto_percentual == Decimal("0.325")


# ---------------------------------------------------------------------------
# TestSimulacaoComSimplesNacional
# ---------------------------------------------------------------------------


class TestSimulacaoComSimplesNacional:
    """Testa simulação com 3 categorias (previdenciário + tributário + simples)."""

    def test_simples_presente_no_resultado(self):
        """Se simples informado, deve estar no resultado."""
        inp = SimulacaoAvancadaInput(
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
            simples=DebitoComponentes(
                principal=Decimal("800"),
                multa=Decimal("200"),
                juros=Decimal("300"),
                encargos=Decimal("100"),
            ),
            is_me_epp=True,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            passivo_pgfn=Decimal("4800"),
            desconto_escolha="MAIOR",
            honorarios_percentual=Decimal("0.20"),
        )
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.simples is not None
        assert resultado.simples.nome == "Simples Nacional"

    def test_simples_none_quando_nao_informado(self):
        """Se simples=None, resultado.simples deve ser None."""
        inp = SimulacaoAvancadaInput(
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
        )
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.simples is None


# ---------------------------------------------------------------------------
# TestCategoriaResult
# ---------------------------------------------------------------------------


class TestCategoriaResult:
    """Testa CategoriaResult dataclass."""

    def test_categoria_tem_fluxo(self):
        """CategoriaResult deve ter fluxo de pagamento."""
        inp = SimulacaoAvancadaInput(
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
        )
        resultado = calcular_simulacao_avancada(inp)

        assert isinstance(resultado.previdenciario, CategoriaResult)
        assert isinstance(resultado.tributario, CategoriaResult)
        assert resultado.previdenciario.fluxo is not None
        assert len(resultado.previdenciario.fluxo) > 0
        assert resultado.tributario.fluxo is not None
        assert len(resultado.tributario.fluxo) > 0

    def test_categoria_saldo_coerente(self):
        """Saldo de cada categoria = total_final do desconto."""
        inp = SimulacaoAvancadaInput(
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
        )
        resultado = calcular_simulacao_avancada(inp)

        assert resultado.previdenciario.saldo == resultado.previdenciario.desconto_result.total_final
        assert resultado.tributario.saldo == resultado.tributario.desconto_result.total_final
