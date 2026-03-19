"""Views DRF para simulação de transação tributária (básica e avançada).

Views são FINAS — delegam ao engine e persistem resultado.
Organization NUNCA vem do payload — sempre do middleware.
"""

from dataclasses import asdict
from decimal import Decimal
from enum import Enum

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import OrgQuerySetMixin
from apps.transacao.constants import ClassificacaoCredito
from apps.transacao.engine import DiagnosticoInput, calcular_diagnostico
from apps.transacao.engine_avancado import (
    DebitoComponentes,
    SimulacaoAvancadaInput,
    calcular_simulacao_avancada,
)
from apps.transacao.models import Simulacao, SimulacaoAvancada
from apps.transacao.serializers import (
    SimulacaoAvancadaRequestSerializer,
    SimulacaoAvancadaResponseSerializer,
    SimulacaoBasicaRequestSerializer,
    SimulacaoListSerializer,
    SimulacaoResponseSerializer,
)


def _decimal_converter(obj):
    """Converte Decimal para string para serialização JSON."""
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _resultado_to_dict(result) -> dict:
    """Converte dataclass result para dict serializável em JSON.

    Converte Decimal para string e remove objetos não serializáveis.
    """
    raw = asdict(result)
    return _sanitize_decimals(raw)


def _sanitize_decimals(obj):
    """Recursivamente converte Decimal/Enum para tipos JSON-serializáveis."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _sanitize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_decimals(item) for item in obj]
    return obj


class SimularBasicoView(APIView):
    """POST: Simula transação tributária básica (diagnóstico prévio).

    Chama engine básico, salva Simulacao, retorna resultado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SimulacaoBasicaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Montar input do engine
        inp = DiagnosticoInput(
            valor_total=data["valor_total_divida"],
            percentual_previdenciario=data["percentual_previdenciario"],
            is_me_epp=data["is_me_epp"],
            classificacao=ClassificacaoCredito(data["classificacao"]),
        )

        # Delegar ao engine
        resultado = calcular_diagnostico(inp)
        resultado_dict = _resultado_to_dict(resultado)

        # Separar calculo_detalhes
        calculo_detalhes = resultado_dict.pop("calculo_detalhes", [])

        # Persistir
        simulacao = Simulacao.objects.create(
            organization=request.organization,
            valor_total_divida=data["valor_total_divida"],
            percentual_previdenciario=data["percentual_previdenciario"],
            is_me_epp=data["is_me_epp"],
            classificacao_credito=data["classificacao"],
            resultado=resultado_dict,
            calculo_detalhes=calculo_detalhes,
        )

        response_serializer = SimulacaoResponseSerializer(simulacao)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class SimularAvancadoView(APIView):
    """POST: Simula transação tributária avançada com decomposição P/M/J/E.

    Chama engine avançado, salva SimulacaoAvancada, retorna resultado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SimulacaoAvancadaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validar empresa_id contra organização
        empresa_id = data.get("empresa_id")
        if empresa_id:
            from apps.empresas.models import Empresa

            if not Empresa.objects.filter(id=empresa_id, organization=request.organization).exists():
                return Response({"error": "Empresa não encontrada"}, status=status.HTTP_404_NOT_FOUND)

        # Montar componentes do engine
        prev = data["previdenciario"]
        trib = data["tributario"]
        simples_data = data.get("simples")

        prev_componentes = DebitoComponentes(
            principal=prev["principal"],
            multa=prev["multa"],
            juros=prev["juros"],
            encargos=prev["encargos"],
        )
        trib_componentes = DebitoComponentes(
            principal=trib["principal"],
            multa=trib["multa"],
            juros=trib["juros"],
            encargos=trib["encargos"],
        )
        simples_componentes = None
        if simples_data:
            simples_componentes = DebitoComponentes(
                principal=simples_data["principal"],
                multa=simples_data["multa"],
                juros=simples_data["juros"],
                encargos=simples_data["encargos"],
            )

        inp = SimulacaoAvancadaInput(
            previdenciario=prev_componentes,
            tributario=trib_componentes,
            simples=simples_componentes,
            is_me_epp=data["is_me_epp"],
            capag_60m=data["capag_60m"],
            passivo_rfb=data["passivo_rfb"],
            passivo_pgfn=data["passivo_pgfn"],
            desconto_escolha=data["desconto_escolha"],
            honorarios_percentual=data["honorarios_percentual"],
        )

        # Delegar ao engine
        resultado = calcular_simulacao_avancada(inp)
        resultado_dict = _resultado_to_dict(resultado)

        # Separar calculo_detalhes
        calculo_detalhes = resultado_dict.pop("calculo_detalhes", [])

        # Persistir
        simulacao = SimulacaoAvancada.objects.create(
            organization=request.organization,
            empresa_id=data.get("empresa_id"),
            passivo_rfb=data["passivo_rfb"],
            capag_60m=data["capag_60m"],
            desconto_escolha=data["desconto_escolha"],
            previdenciario_principal=prev["principal"],
            previdenciario_multa=prev["multa"],
            previdenciario_juros=prev["juros"],
            previdenciario_encargos=prev["encargos"],
            tributario_principal=trib["principal"],
            tributario_multa=trib["multa"],
            tributario_juros=trib["juros"],
            tributario_encargos=trib["encargos"],
            simples_principal=simples_data["principal"] if simples_data else 0,
            simples_multa=simples_data["multa"] if simples_data else 0,
            simples_juros=simples_data["juros"] if simples_data else 0,
            simples_encargos=simples_data["encargos"] if simples_data else 0,
            resultado=resultado_dict,
            calculo_detalhes=calculo_detalhes,
        )

        response_serializer = SimulacaoAvancadaResponseSerializer(simulacao)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class HistoricoView(OrgQuerySetMixin, generics.ListAPIView):
    """GET: Lista simulações básicas da organização com paginação."""

    permission_classes = [IsAuthenticated]
    serializer_class = SimulacaoListSerializer
    queryset = Simulacao.objects.all()


class SimulacaoDetalheView(OrgQuerySetMixin, generics.RetrieveAPIView):
    """GET: Detalhe de uma simulação básica."""

    permission_classes = [IsAuthenticated]
    serializer_class = SimulacaoResponseSerializer
    queryset = Simulacao.objects.all()
