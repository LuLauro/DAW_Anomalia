from django.contrib import admin
from .models import Computador


@admin.register(Computador)
class ComputadorAdmin(admin.ModelAdmin):
    list_display = ('numero_identificacao', 'sala',
                    'marca', 'modelo', 'data_aquisicao')
    list_filter = ('sala', 'marca')
    search_fields = ('numero_identificacao', 'marca', 'modelo')
