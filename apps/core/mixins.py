"""Mixins de isolamento multi-tenant para ViewSets DRF.

SEGURANCA CRITICA: Estes mixins garantem que um usuario NUNCA acesse
dados de outra organizacao. TODOS os ViewSets de negocio DEVEM usar estes mixins.
"""

from rest_framework.exceptions import PermissionDenied


class OrgQuerySetMixin:
    """Filtra queryset por organization do request.

    SEGURANCA: Se request.organization e None, retorna qs.none()
    para NUNCA expor dados sem filtro de organizacao.
    """

    def get_queryset(self):
        """Retorna queryset filtrado pela organizacao do usuario autenticado."""
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            return qs.none()
        return qs.filter(organization=org)


class OrgCreateMixin:
    """Seta organization automaticamente ao criar objetos.

    SEGURANCA: Impede que um usuario crie objetos em outra organizacao,
    mesmo que envie organization_id manualmente no payload.
    SEMPRE usa a org do request, IGNORA qualquer org_id no payload.
    """

    def perform_create(self, serializer):
        """Persiste o objeto com a organizacao do request."""
        org = getattr(self.request, "organization", None)
        if org is None:
            raise PermissionDenied("Usuário não pertence a nenhuma organização.")
        serializer.save(organization=org)
