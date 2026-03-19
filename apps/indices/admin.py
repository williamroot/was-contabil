"""Admin registration para IndiceEconomico."""

from django.contrib import admin

from apps.indices.models import IndiceEconomico


@admin.register(IndiceEconomico)
class IndiceEconomicoAdmin(admin.ModelAdmin):
    """Admin para IndiceEconomico — visualização de séries BCB."""

    list_display = ("serie_nome", "serie_codigo", "data_referencia", "valor", "created_at")
    list_filter = ("serie_codigo", "serie_nome")
    search_fields = ("serie_nome",)
    ordering = ("-data_referencia",)
    date_hierarchy = "data_referencia"
    readonly_fields = ("created_at",)
