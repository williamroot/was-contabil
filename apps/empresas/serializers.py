"""Serializers da app Empresa: criação, resposta completa e listagem resumida."""

import re

from rest_framework import serializers

from apps.empresas.models import Empresa

PORTE_VALIDOS = {"ME/EPP", "DEMAIS"}


class EmpresaCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação/atualização de Empresa.

    Validações:
    - CNPJ: aceita com pontuação, mas deve ter exatamente 14 dígitos.
    - Porte: deve ser 'ME/EPP' ou 'DEMAIS'.
    """

    class Meta:
        model = Empresa
        fields = ["nome", "cnpj", "porte", "honorarios_percentual", "observacoes"]

    def validate_cnpj(self, value):
        """Valida que o CNPJ tem exatamente 14 dígitos (ignora pontuação)."""
        digitos = re.sub(r"\D", "", value)
        if len(digitos) != 14:
            raise serializers.ValidationError("CNPJ deve conter exatamente 14 dígitos.")
        return value

    def validate_porte(self, value):
        """Valida que o porte é um dos valores permitidos."""
        if value not in PORTE_VALIDOS:
            raise serializers.ValidationError(
                f"Porte inválido. Valores permitidos: {', '.join(sorted(PORTE_VALIDOS))}."
            )
        return value


class EmpresaResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta completa — usado em create, retrieve, update."""

    class Meta:
        model = Empresa
        fields = [
            "id",
            "nome",
            "cnpj",
            "porte",
            "honorarios_percentual",
            "observacoes",
            "created_at",
        ]
        read_only_fields = fields


class EmpresaListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem — sem campos pesados."""

    class Meta:
        model = Empresa
        fields = ["id", "nome", "cnpj", "porte"]
        read_only_fields = fields
