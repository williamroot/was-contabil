"""Middleware de multi-tenant: seta request.organization baseado no usuário logado."""

from apps.core.models import Membership


class OrganizationMiddleware:
    """Seta request.organization baseado no usuário autenticado.

    Busca o primeiro Membership do usuário e seta a organização associada.
    Se o usuário não está autenticado ou não pertence a nenhuma organização,
    request.organization fica None.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        if request.user.is_authenticated:
            membership = (
                Membership.objects.filter(user=request.user)
                .select_related("organization")
                .order_by("joined_at")
                .first()
            )
            if membership:
                request.organization = membership.organization
        return self.get_response(request)
