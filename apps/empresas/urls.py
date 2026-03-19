"""URLs da app Empresa — CRUD via DRF Router."""

from rest_framework.routers import DefaultRouter

from apps.empresas.views import EmpresaViewSet

app_name = "empresas"

router = DefaultRouter()
router.register("", EmpresaViewSet, basename="empresa")

urlpatterns = router.urls
