from django.contrib import admin
from .models import Anomalia


@admin.register(Anomalia)
class AnomaliaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'computador', 'estado',
                    'data_registo', 'reportado_por')
    list_filter = ('estado', 'data_registo')
    search_fields = ('titulo', 'descricao')
