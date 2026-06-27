from django.contrib import admin
from .models import Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("numero", "descricao", "coordinator")
    list_filter = ("coordinator",)
    search_fields = ("numero", "coordinator__username", "coordinator__first_name", "coordinator__last_name")
