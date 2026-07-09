from django import forms
from .models import Sala


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['numero', 'descricao']
        labels = {
            'numero': 'Número',
            'descricao': 'Descrição',
        }
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
