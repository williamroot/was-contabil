"""Serializers DRF para simulação de transação tributária (básica e avançada).

Validação rigorosa de entrada + serialização de resposta.
"""

from rest_framework import serializers

from apps.transacao.models import Simulacao, SimulacaoAvancada

CLASSIFICACAO_VALIDAS = {"A", "B", "C", "D"}
DESCONTO_ESCOLHA_VALIDOS = {"MAIOR", "MENOR"}


# ---------------------------------------------------------------------------
# Nested serializers
# ---------------------------------------------------------------------------


class DebitoComponentesSerializer(serializers.Serializer):
    """Composição de um débito em P/M/J/E (Principal, Multa, Juros, Encargos)."""

    principal = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    multa = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    juros = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    encargos = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)


# ---------------------------------------------------------------------------
# Request serializers
# ---------------------------------------------------------------------------


class SimulacaoBasicaRequestSerializer(serializers.Serializer):
    """Serializer de entrada para simulação básica de transação tributária."""

    valor_total_divida = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=1,
        help_text="Valor consolidado total da dívida (mínimo R$ 1,00).",
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

    def validate_classificacao(self, value):
        """Valida que a classificação é A, B, C ou D."""
        value = value.upper()
        if value not in CLASSIFICACAO_VALIDAS:
            raise serializers.ValidationError(f"Classificação inválida: {value}. Valores permitidos: A, B, C, D.")
        return value


class SimulacaoAvancadaRequestSerializer(serializers.Serializer):
    """Serializer de entrada para simulação avançada de transação tributária."""

    empresa_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="UUID da empresa cadastrada (opcional).",
    )
    passivo_rfb = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text="Passivo total junto à RFB.",
    )
    passivo_pgfn = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text="Passivo total junto à PGFN (base para desconto).",
    )
    capag_60m = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text="Capacidade de pagamento estimada em 60 meses.",
    )
    is_me_epp = serializers.BooleanField(
        default=False,
        help_text="True se o contribuinte é ME, EPP ou pessoa física.",
    )
    desconto_escolha = serializers.CharField(
        default="MAIOR",
        help_text="'MAIOR' (máximo) ou 'MENOR' (metade do máximo).",
    )
    honorarios_percentual = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=1,
        default=0,
        help_text="Percentual de honorários (0 a 1).",
    )
    previdenciario = DebitoComponentesSerializer(help_text="Débito previdenciário P/M/J/E.")
    tributario = DebitoComponentesSerializer(help_text="Débito tributário P/M/J/E.")
    simples = DebitoComponentesSerializer(
        required=False,
        allow_null=True,
        help_text="Débito simples nacional P/M/J/E (opcional).",
    )

    def validate_desconto_escolha(self, value):
        """Valida que a escolha de desconto é MAIOR ou MENOR."""
        value = value.upper()
        if value not in DESCONTO_ESCOLHA_VALIDOS:
            raise serializers.ValidationError(f"Escolha inválida: {value}. Valores permitidos: MAIOR, MENOR.")
        return value


# ---------------------------------------------------------------------------
# Response serializers
# ---------------------------------------------------------------------------


class SimulacaoResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta completa de simulação básica."""

    class Meta:
        model = Simulacao
        fields = [
            "id",
            "razao_social",
            "cnpj",
            "valor_total_divida",
            "percentual_previdenciario",
            "is_me_epp",
            "classificacao_credito",
            "resultado",
            "calculo_detalhes",
            "versao_calculo",
            "created_at",
        ]
        read_only_fields = fields


class SimulacaoListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de simulações."""

    class Meta:
        model = Simulacao
        fields = [
            "id",
            "razao_social",
            "cnpj",
            "valor_total_divida",
            "classificacao_credito",
            "created_at",
        ]
        read_only_fields = fields


class SimulacaoAvancadaResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta completa de simulação avançada."""

    class Meta:
        model = SimulacaoAvancada
        fields = [
            "id",
            "passivo_rfb",
            "capag_60m",
            "desconto_escolha",
            "resultado",
            "calculo_detalhes",
            "versao_calculo",
            "created_at",
        ]
        read_only_fields = fields
