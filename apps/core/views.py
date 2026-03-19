"""Views do app core — página inicial, login, convites e utilitários."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.core.models import Invitation


class HomeView(LoginRequiredMixin, TemplateView):
    """Página inicial do WAS Contábil.

    Redireciona para login se o usuário não está autenticado.
    Exibe dashboard com links para os módulos principais.
    """

    template_name = "core/home.html"


class LoginPageView(TemplateView):
    """Página de login customizada (override do allauth)."""

    template_name = "core/login.html"


class InvitePageView(TemplateView):
    """Página de aceitar convite por token."""

    template_name = "core/invite.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get("token", "")
        invitation = Invitation.objects.filter(token=token).first()
        if not invitation or invitation.is_expired or invitation.is_accepted:
            context["error"] = "Convite inválido, expirado ou já utilizado"
            context["invitation"] = None
        else:
            context["invitation"] = invitation
        return context


class OrganizationSetupPageView(LoginRequiredMixin, TemplateView):
    """Página de configuração da organização após primeiro login."""

    template_name = "core/organization_setup.html"
