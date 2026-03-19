"""Serializers DRF para comparação de modalidades CAPAG vs TPV."""

from rest_framework import serializers

CLASSIFICACAO_VALIDAS = {"A", "B", "C", "D"}


class ComparacaoRequestSerializer(serializers.Serializer):
    """Serializer de entrada para comparação de modalidades."""

    valor_total = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=1,
        help_text="Valor consolidado total da dívida.",
    )
    percentual_previdenciario = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        min_value=0,
        max_value=1,
        help_text="Fração (0 a 1) do valor que é previdenciário.",
    )
    is_me_epp = serializers.BooleanField(
        default=False,
        help_text="True se o contribuinte é ME, EPP ou pessoa física.",
    )
    classificacao = serializers.CharField(
        default="D",
        help_text="Classificação CAPAG (A, B, C ou D).",
    )
    tpv_elegivel = serializers.BooleanField(
        default=False,
        help_text="True se o contribuinte é elegível para TPV.",
    )

    def validate_classificacao(self, value):
        """Valida que a classificação é A, B, C ou D."""
        value = value.upper()
        if value not in CLASSIFICACAO_VALIDAS:
            raise serializers.ValidationError(f"Classificação inválida: {value}. Valores permitidos: A, B, C, D.")
        return value


class ComparacaoResponseSerializer(serializers.Serializer):
    """Serializer de resposta da comparação de modalidades."""

    tpv_disponivel = serializers.BooleanField()
    tpv_melhor_valor_final = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        allow_null=True,
    )
    tpv_economia = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        allow_null=True,
    )
    capacidade_valor_final = serializers.DecimalField(max_digits=15, decimal_places=2)
    capacidade_economia = serializers.DecimalField(max_digits=15, decimal_places=2)
    recomendacao = serializers.CharField()
    economia_diferenca = serializers.DecimalField(max_digits=15, decimal_places=2)
