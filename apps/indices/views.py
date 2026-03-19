"""Views DRF para índices econômicos (SELIC).

Views são FINAS — delegam ao service/client.
"""

from datetime import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.indices.models import IndiceEconomico
from apps.indices.serializers import IndiceSerializer, SelicAcumuladaResponseSerializer
from apps.indices.service import IndicesService

SERIE_SELIC_MENSAL = 4390


class SelicUltimosView(APIView):
    """GET: Retorna últimos N índices SELIC mensais do banco local.

    Query param: n (default 12).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            n = int(request.query_params.get("n", 12))
            n = max(1, min(n, 120))  # Limitar entre 1 e 120
        except (TypeError, ValueError):
            n = 12

        indices = IndiceEconomico.objects.filter(
            serie_codigo=SERIE_SELIC_MENSAL,
        ).order_by(
            "-data_referencia"
        )[:n]

        serializer = IndiceSerializer(indices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SelicAcumuladaView(APIView):
    """GET: Retorna fator SELIC acumulado entre duas datas.

    Query params: data_inicial (YYYY-MM-DD), data_final (YYYY-MM-DD).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data_inicial_str = request.query_params.get("data_inicial")
        data_final_str = request.query_params.get("data_final")

        if not data_inicial_str or not data_final_str:
            return Response(
                {"detail": "Parâmetros 'data_inicial' e 'data_final' são obrigatórios (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato de data inválido. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = IndicesService()
        fator = service.get_selic_acumulada(data_inicial, data_final)

        resultado = {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "fator_acumulado": fator,
        }

        response_serializer = SelicAcumuladaResponseSerializer(resultado)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
