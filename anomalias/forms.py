from django import forms
from .models import Anomalia, Computador
from salas.models import Sala


class AnomaliaForm(forms.ModelForm):
    class Meta:
        model = Anomalia
        fields = ['titulo', 'descricao', 'computador']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'computador': forms.Select(attrs={'class': 'form-control'}),
        }


class AnomaliaFilterForm(forms.Form):
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        empty_label="Todas as Salas",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos os Estados')] + Anomalia.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Anomalia
        fields = ['observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escreva sua observação aqui...'
            }),
        }
        
class FiltroHistoricoForm(forms.Form):
    
    data_resolvida = forms.DateField(
    required=False,
    label='Data de Resolução',
    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        label='Sala',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    computador = forms.ModelChoiceField(
        queryset=Computador.objects.all(),
        required=False,
        label='Computador',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class RelatorioAnomaliasForm(forms.Form):
    data_inicio = forms.DateField(
        required=False,
        label='De',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    data_fim = forms.DateField(
        required=False,
        label='Até',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        label='Sala',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    computador = forms.ModelChoiceField(
        queryset=Computador.objects.all(),
        required=False,
        label='Computador',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    
class AnomaliaGeralForm(forms.ModelForm):
    class Meta:
        model = Anomalia
        fields = ['titulo', 'descricao', 'sala', 'tipo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sala': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
        }
        
