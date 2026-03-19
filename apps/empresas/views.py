"""ViewSet de Empresa — CRUD com isolamento multi-tenant.

SEGURANCA: OrgQuerySetMixin filtra queryset por request.organization.
OrgCreateMixin seta organization automaticamente ao criar.
"""

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.mixins import OrgCreateMixin, OrgQuerySetMixin
from apps.empresas.models import Empresa
from apps.empresas.serializers import (
    EmpresaCreateSerializer,
    EmpresaListSerializer,
    EmpresaResponseSerializer,
)


class EmpresaViewSet(OrgQuerySetMixin, OrgCreateMixin, viewsets.ModelViewSet):
    """CRUD completo de Empresa com isolamento multi-tenant.

    - list: retorna empresas da organização do usuário (com busca opcional)
    - create: cria empresa vinculada à organização do request
    - retrieve/update/destroy: opera apenas em empresas da mesma organização
    """

    queryset = Empresa.objects.all()

    def get_serializer_class(self):
        """Retorna serializer adequado para cada ação."""
        if self.action == "list":
            return EmpresaListSerializer
        if self.action in ("create", "update", "partial_update"):
            return EmpresaCreateSerializer
        return EmpresaResponseSerializer

    def get_queryset(self):
        """Filtra por organização (via mixin) e aplica busca se presente."""
        qs = super().get_queryset()
        busca = self.request.query_params.get("busca")
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(cnpj__icontains=busca))
        return qs

    def create(self, request, *args, **kwargs):
        """Cria empresa e retorna resposta com serializer completo."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Resposta com serializer completo (inclui id, created_at)
        response_serializer = EmpresaResponseSerializer(serializer.instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Atualiza empresa e retorna resposta com serializer completo."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        response_serializer = EmpresaResponseSerializer(instance)
        return Response(response_serializer.data)
