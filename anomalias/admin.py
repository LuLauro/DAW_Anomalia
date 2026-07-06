from django.contrib import admin

from .models import Anomalia, Perfil


@admin.register(Anomalia)
class AnomaliaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "computador",
        "estado",
        "prioridade",
        "data_registo",
        "reportado_por",
    )
    list_filter = ("estado", "prioridade", "data_registo")
    search_fields = ("titulo", "descricao")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "tipo")
    list_filter = ("tipo",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
