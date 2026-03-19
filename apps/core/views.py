"""Views do app core — página inicial, login, convites e utilitários."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.core.models import Invitation


class LandingView(TemplateView):
    """Landing page publica do WAS Contabil.

    Se o usuario ja esta logado, redireciona para o dashboard.
    """

    template_name = "core/landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from django.shortcuts import redirect

            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)


class HomeView(LoginRequiredMixin, TemplateView):
    """Dashboard do WAS Contabil (area logada).

    Redireciona para login se o usuario nao esta autenticado.
    Exibe dashboard com links para os modulos principais.
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
