"""Serializers DRF para índices econômicos (SELIC, IPCA)."""

from rest_framework import serializers


class IndiceSerializer(serializers.Serializer):
    """Serializer de um índice econômico individual."""

    data = serializers.DateField(source="data_referencia")
    valor = serializers.DecimalField(max_digits=12, decimal_places=6)


class SelicAcumuladaResponseSerializer(serializers.Serializer):
    """Serializer de resposta para SELIC acumulada entre datas."""

    data_inicial = serializers.DateField()
    data_final = serializers.DateField()
    fator_acumulado = serializers.DecimalField(max_digits=20, decimal_places=10)
