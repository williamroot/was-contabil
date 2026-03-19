"""Views de pagina para o modulo de empresas."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class EmpresasPageView(LoginRequiredMixin, TemplateView):
    """Pagina de listagem e cadastro de empresas."""

    template_name = "empresas/list.html"
