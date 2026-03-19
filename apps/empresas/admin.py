"""Admin da app Empresa."""

from django.contrib import admin

from apps.empresas.models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Configuração do admin para Empresa."""

    list_display = ["nome", "cnpj", "porte", "organization", "created_at"]
    list_filter = ["porte", "organization"]
    search_fields = ["nome", "cnpj"]
    readonly_fields = ["id", "created_at"]
