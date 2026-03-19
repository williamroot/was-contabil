import django_rq.urls as rq_urls

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import include, path

# Proteger todas as views do django-rq com staff_member_required
for url_pattern in rq_urls.urlpatterns:
    url_pattern.callback = staff_member_required(url_pattern.callback)

urlpatterns = [
    path("health/", lambda r: JsonResponse({"status": "ok"}), name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("convites/", include("apps.core.urls_invitations")),
    path("django-rq/", include("django_rq.urls")),
    # API REST (preparado para Vue frontend)
    path("api/v1/empresas/", include("apps.empresas.urls")),
    path(
        "api/v1/transacao/",
        include("apps.transacao.urls", namespace="transacao-api"),
    ),
    path(
        "api/v1/tpv/",
        include("apps.tpv.urls", namespace="tpv-api"),
    ),
    path("api/v1/indices/", include("apps.indices.urls")),
    path("api/v1/comparador/", include("apps.comparador.urls")),
    # PDF downloads
    path("pdf/", include("apps.pdf.urls")),
    # Frontend templates (HTMX) — páginas de módulos
    path("transacao/", include("apps.transacao.urls_pages")),
    path("tpv/", include("apps.tpv.urls_pages")),
    path("empresas/", include("apps.empresas.urls_pages")),
    path("comparador/", include("apps.comparador.urls_pages")),
    # Frontend templates (HTMX) — core (home, login, convites)
    path("", include("apps.core.urls")),
]
