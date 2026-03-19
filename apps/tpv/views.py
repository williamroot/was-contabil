"""Views DRF para simulação TPV — Transação de Pequeno Valor.

Views são FINAS — delegam ao engine/validators e persistem resultado.
Organization NUNCA vem do payload — sempre do middleware.
"""

import io
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import OrgQuerySetMixin
from apps.tpv.engine import CDAInput, TPVInput, calcular_tpv, calcular_tpv_todas_faixas
from apps.tpv.importers import parse_cdas_csv, parse_cdas_excel
from apps.tpv.models import SimulacaoTPV
from apps.tpv.serializers import (
    SimulacaoTPVListSerializer,
    SimulacaoTPVResponseSerializer,
    TPVSimulacaoRequestSerializer,
    TPVWizardRequestSerializer,
)
from apps.tpv.validators import validar_elegibilidade_wizard


def _sanitize_decimals(obj):
    """Recursivamente converte Decimal para string em dicts/lists."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_decimals(item) for item in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def _resultado_to_dict(result) -> dict:
    """Converte dataclass result para dict serializável em JSON."""
    raw = asdict(result)
    return _sanitize_decimals(raw)


class SimularTPVView(APIView):
    """POST: Simula TPV para um conjunto de CDAs.

    Valida CDAs, calcula entrada/desconto/parcelas, salva resultado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TPVSimulacaoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Montar input do engine
        cdas = [
            CDAInput(
                numero=cda["numero"],
                valor=cda["valor"],
                data_inscricao=cda["data_inscricao"],
            )
            for cda in data["cdas"]
        ]

        inp = TPVInput(
            cdas=cdas,
            parcelas_entrada=data["parcelas_entrada"],
            parcelas_saldo=data["parcelas_saldo"],
            salario_minimo=data["salario_minimo"],
            data_simulacao=date.today(),
        )

        # Delegar ao engine
        resultado = calcular_tpv(inp)
        resultado_dict = _resultado_to_dict(resultado)

        # Persistir
        simulacao = SimulacaoTPV.objects.create(
            organization=request.organization,
            nome_contribuinte=data.get("nome_contribuinte", ""),
            cpf_cnpj=data.get("cpf_cnpj", ""),
            tipo_porte=data["tipo_porte"],
            salario_minimo=data["salario_minimo"],
            parcelas_entrada=data["parcelas_entrada"],
            parcelas_saldo=data["parcelas_saldo"],
            resultado=resultado_dict,
        )

        response_serializer = SimulacaoTPVResponseSerializer(simulacao)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class WizardElegibilidadeView(APIView):
    """POST: Wizard simplificado de elegibilidade TPV.

    Valida elegibilidade e, se elegível, calcula todas as faixas de desconto.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TPVWizardRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Delegar ao validator
        elegibilidade = validar_elegibilidade_wizard(
            tipo_contribuinte=data["tipo_contribuinte"],
            possui_cda_acima_limite=data["possui_cda_acima_limite"],
            valor_total=data["valor_total"],
            todas_cdas_mais_1_ano=data["todas_cdas_mais_1_ano"],
            salario_minimo=data["salario_minimo"],
        )

        resposta = {
            "elegivel": elegibilidade.elegivel,
            "criterios": elegibilidade.criterios,
            "mensagem": elegibilidade.mensagem,
        }

        # Se elegível, calcular faixas
        if elegibilidade.elegivel:
            faixas_result = calcular_tpv_todas_faixas(data["valor_total"])
            resposta["faixas"] = _resultado_to_dict(faixas_result)

        return Response(resposta, status=status.HTTP_200_OK)


class ImportarCDAsView(APIView):
    """POST: Importa CDAs de arquivo CSV ou Excel.

    Aceita multipart/form-data com campo 'arquivo'.
    Retorna lista de CDAs parseadas e erros por linha.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return Response(
                {"detail": "Campo 'arquivo' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nome = arquivo.name.lower()

        if nome.endswith(".csv"):
            texto = io.TextIOWrapper(arquivo, encoding="utf-8")
            parse_result = parse_cdas_csv(texto)
        elif nome.endswith(".xlsx"):
            conteudo = arquivo.read()
            parse_result = parse_cdas_excel(conteudo)
        else:
            return Response(
                {"detail": "Formato não suportado. Use CSV ou XLSX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cdas_data = [
            {
                "numero": cda.numero,
                "valor": str(cda.valor),
                "data_inscricao": cda.data_inscricao.isoformat(),
            }
            for cda in parse_result.cdas
        ]

        return Response(
            {
                "cdas": cdas_data,
                "total": len(cdas_data),
                "erros": parse_result.erros,
            },
            status=status.HTTP_200_OK,
        )


class HistoricoTPVView(OrgQuerySetMixin, generics.ListAPIView):
    """GET: Lista simulações TPV da organização com paginação."""

    permission_classes = [IsAuthenticated]
    serializer_class = SimulacaoTPVListSerializer
    queryset = SimulacaoTPV.objects.all()
