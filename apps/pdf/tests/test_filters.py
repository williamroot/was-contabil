"""Testes para template filters do modulo PDF.

Valida que o filtro as_percent converte corretamente decimal para percentual.
"""

from decimal import Decimal

import pytest

from apps.pdf.templatetags.pdf_filters import as_percent


class TestAsPercentFilter:
    """Testa o filtro as_percent que converte decimal para percentual."""

    def test_decimal_065_retorna_65(self):
        """0.65 deve retornar 65.0."""
        assert as_percent(Decimal("0.65")) == 65.0

    def test_decimal_020_retorna_20(self):
        """0.20 deve retornar 20.0."""
        assert as_percent(Decimal("0.20")) == 20.0

    def test_decimal_050_retorna_50(self):
        """0.50 deve retornar 50.0."""
        assert as_percent(Decimal("0.50")) == 50.0

    def test_decimal_070_retorna_70(self):
        """0.70 deve retornar 70.0."""
        assert as_percent(Decimal("0.70")) == 70.0

    def test_zero_retorna_zero(self):
        """0 deve retornar 0."""
        assert as_percent(Decimal("0")) == 0.0

    def test_um_retorna_100(self):
        """1.0 deve retornar 100.0."""
        assert as_percent(Decimal("1.0")) == 100.0

    def test_string_numerica_funciona(self):
        """String numerica '0.65' deve funcionar."""
        assert as_percent("0.65") == 65.0

    def test_float_funciona(self):
        """Float 0.65 deve funcionar."""
        assert as_percent(0.65) == pytest.approx(65.0)

    def test_valor_invalido_retorna_original(self):
        """Valor nao numerico deve retornar o valor original."""
        assert as_percent("abc") == "abc"

    def test_none_retorna_none(self):
        """None deve retornar None."""
        assert as_percent(None) is None


class TestAsPercentNoTemplate:
    """Testa que o filtro as_percent funciona no contexto de template Django."""

    @pytest.mark.django_db
    def test_percentual_renderiza_corretamente(self):
        """Template com as_percent deve renderizar 65% (ou 65,0%) em vez de 0,7%."""
        from django.template import Context, Template

        template = Template("{% load pdf_filters %}{{ valor|as_percent|floatformat:1 }}%")
        context = Context({"valor": Decimal("0.65")})
        rendered = template.render(context)

        # pt-br usa virgula como separador decimal
        assert "65" in rendered
        assert "0,7%" not in rendered
        assert "0.7%" not in rendered

    @pytest.mark.django_db
    def test_honorarios_percentual_renderiza_corretamente(self):
        """Honorarios 0.20 deve renderizar como 20%."""
        from django.template import Context, Template

        template = Template("{% load pdf_filters %}{{ valor|as_percent|floatformat:0 }}%")
        context = Context({"valor": Decimal("0.20")})
        rendered = template.render(context)

        assert "20%" in rendered
