from django import forms
from django.contrib import admin

from .models import PerfilCoordenador


class PerfilCoordenadorAdminForm(forms.ModelForm):
    class Meta:
        model = PerfilCoordenador
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = (
            self.fields["user"]
            .queryset.filter(groups__name="Coordenador")
            .distinct()
            .order_by("username")
        )


@admin.register(PerfilCoordenador)
class PerfilCoordenadorAdmin(admin.ModelAdmin):
    form = PerfilCoordenadorAdminForm
    filter_horizontal = ("salas",)
    list_display = ("user", "total_salas")
    search_fields = ("user__username", "user__first_name", "user__last_name", "salas__numero")

    @admin.display(description="Salas")
    def total_salas(self, obj):
        return obj.salas.count()
