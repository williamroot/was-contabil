"""Views para comparação de modalidades CAPAG vs TPV.

Views são FINAS — delegam ao service.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comparador.serializers import ComparacaoRequestSerializer, ComparacaoResponseSerializer
from apps.comparador.service import comparar_modalidades
from apps.transacao.constants import ClassificacaoCredito


class CompararView(APIView):
    """POST: Compara modalidades CAPAG vs TPV e recomenda a melhor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ComparacaoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Delegar ao service
        resultado = comparar_modalidades(
            valor_total=data["valor_total"],
            percentual_previdenciario=data["percentual_previdenciario"],
            is_me_epp=data["is_me_epp"],
            classificacao=ClassificacaoCredito(data["classificacao"]),
            tpv_elegivel=data["tpv_elegivel"],
        )

        response_serializer = ComparacaoResponseSerializer(resultado)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ComparadorPageView(LoginRequiredMixin, TemplateView):
    """Pagina do comparador de modalidades."""

    template_name = "comparador/comparacao.html"
