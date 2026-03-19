"""Serializers DRF para simulação TPV — Transação de Pequeno Valor.

Validação rigorosa de entrada + serialização de resposta.
"""

from rest_framework import serializers

from apps.tpv.constants import TIPOS_CONTRIBUINTE_ELEGIVEIS
from apps.tpv.models import SimulacaoTPV

PARCELAS_SALDO_VALIDAS = {7, 12, 30, 55}


# ---------------------------------------------------------------------------
# Request serializers
# ---------------------------------------------------------------------------


class CDARequestSerializer(serializers.Serializer):
    """Dados de uma CDA para simulação TPV."""

    numero = serializers.CharField(
        max_length=50,
        help_text="Número identificador da CDA.",
    )
    valor = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text="Valor consolidado da CDA.",
    )
    data_inscricao = serializers.DateField(
        help_text="Data de inscrição da CDA (YYYY-MM-DD).",
    )


class TPVSimulacaoRequestSerializer(serializers.Serializer):
    """Serializer de entrada para simulação TPV completa."""

    nome_contribuinte = serializers.CharField(
        max_length=300,
        required=False,
        default="",
        help_text="Nome do contribuinte.",
    )
    cpf_cnpj = serializers.CharField(
        max_length=18,
        required=False,
        default="",
        help_text="CPF ou CNPJ do contribuinte.",
    )
    tipo_porte = serializers.CharField(
        help_text="Tipo do contribuinte: PF, ME ou EPP.",
    )
    salario_minimo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1,
        help_text="Valor do salário mínimo vigente.",
    )
    parcelas_entrada = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Número de parcelas da entrada (1 a 5).",
    )
    parcelas_saldo = serializers.IntegerField(
        help_text="Número de parcelas do saldo (7, 12, 30 ou 55).",
    )
    cdas = CDARequestSerializer(
        many=True,
        help_text="Lista de CDAs para simulação.",
    )

    def validate_tipo_porte(self, value):
        """Valida que o tipo de porte é elegível para TPV."""
        value = value.upper()
        if value not in TIPOS_CONTRIBUINTE_ELEGIVEIS:
            raise serializers.ValidationError(
                f"Tipo inválido: {value}. Valores permitidos: {', '.join(TIPOS_CONTRIBUINTE_ELEGIVEIS)}."
            )
        return value

    def validate_parcelas_saldo(self, value):
        """Valida que o número de parcelas do saldo é uma faixa válida."""
        if value not in PARCELAS_SALDO_VALIDAS:
            raise serializers.ValidationError(
                f"Parcelas inválidas: {value}. Faixas válidas: {sorted(PARCELAS_SALDO_VALIDAS)}."
            )
        return value

    def validate_cdas(self, value):
        """Valida que há pelo menos uma CDA na lista."""
        if not value:
            raise serializers.ValidationError("Deve informar pelo menos uma CDA.")
        return value


class TPVWizardRequestSerializer(serializers.Serializer):
    """Serializer de entrada para wizard de elegibilidade TPV."""

    tipo_contribuinte = serializers.CharField(
        help_text="Tipo do contribuinte (PF, ME, EPP, PJ, etc.).",
    )
    possui_cda_acima_limite = serializers.BooleanField(
        help_text="True se possui alguma CDA acima de 60 SM.",
    )
    valor_total = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0,
        help_text="Valor total das CDAs.",
    )
    todas_cdas_mais_1_ano = serializers.BooleanField(
        help_text="True se todas as CDAs estão inscritas há mais de 1 ano.",
    )
    salario_minimo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1,
        help_text="Valor do salário mínimo vigente.",
    )


# ---------------------------------------------------------------------------
# Response serializers
# ---------------------------------------------------------------------------


class SimulacaoTPVResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta de simulação TPV."""

    class Meta:
        model = SimulacaoTPV
        fields = [
            "id",
            "nome_contribuinte",
            "cpf_cnpj",
            "tipo_porte",
            "salario_minimo",
            "parcelas_entrada",
            "parcelas_saldo",
            "resultado",
            "created_at",
        ]
        read_only_fields = fields


class SimulacaoTPVListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de simulações TPV."""

    class Meta:
        model = SimulacaoTPV
        fields = [
            "id",
            "nome_contribuinte",
            "cpf_cnpj",
            "tipo_porte",
            "created_at",
        ]
        read_only_fields = fields
