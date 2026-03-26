from django import forms
from django.utils.datastructures import MultiValueDict
import os
from .models import Anomalia
from computadores.models import Computador
from salas.models import Sala

BASE_WIDGETS = {'class': 'form-control'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return MultiValueDict(files).getlist(name)


class MultipleFileField(forms.FileField):
    def __init__(self, *args, allowed_exts=None, max_size=None, **kwargs):
        self.allowed_exts = allowed_exts or set()
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        _validar_arquivos(data, self.allowed_exts, self.max_size)
        return data

def _validar_arquivos(arquivos, extensoes_permitidas, tamanho_maximo):
    for arquivo in arquivos:
        ext = os.path.splitext(arquivo.name)[1].lower().lstrip(".")
        if ext not in extensoes_permitidas:
            raise forms.ValidationError("Tipo de ficheiro nÃ£o permitido.")
        if arquivo.size > tamanho_maximo:
            raise forms.ValidationError("Tamanho de ficheiro excede o limite permitido.")
    return arquivos

class AnomaliaForm(forms.ModelForm):
    imagens = MultipleFileField(
        required=False,
        allowed_exts={"jpg", "jpeg", "png"},
        max_size=MAX_IMAGE_SIZE,
        widget=MultipleFileInput(attrs={"accept": "image/png,image/jpeg"}),
        label="Imagens (opcional)",
    )
    videos = MultipleFileField(
        required=False,
        allowed_exts={"mp4"},
        max_size=MAX_VIDEO_SIZE,
        widget=MultipleFileInput(attrs={"accept": "video/mp4"}),
        label="Videos (opcional)",
    )

    class Meta:
        model = Anomalia
        fields = ['titulo', 'descricao', 'computador']
        widgets = {
            'titulo': forms.TextInput(attrs=BASE_WIDGETS),
            'descricao': forms.Textarea(attrs={**BASE_WIDGETS, 'rows': 3}),
            'computador': forms.Select(attrs=BASE_WIDGETS),
        }

    def clean_imagens(self):
        arquivos = self.files.getlist("imagens")
        return _validar_arquivos(arquivos, {"jpg", "jpeg", "png"}, MAX_IMAGE_SIZE)

    def clean_videos(self):
        arquivos = self.files.getlist("videos")
        return _validar_arquivos(arquivos, {"mp4"}, MAX_VIDEO_SIZE)

class AnomaliaGeralForm(forms.ModelForm):
    imagens = MultipleFileField(
        required=False,
        allowed_exts={"jpg", "jpeg", "png"},
        max_size=MAX_IMAGE_SIZE,
        widget=MultipleFileInput(attrs={"accept": "image/png,image/jpeg"}),
        label="Imagens (opcional)",
    )
    videos = MultipleFileField(
        required=False,
        allowed_exts={"mp4"},
        max_size=MAX_VIDEO_SIZE,
        widget=MultipleFileInput(attrs={"accept": "video/mp4"}),
        label="Videos (opcional)",
    )

    class Meta:
        model = Anomalia
        fields = ['titulo', 'descricao', 'sala', 'tipo']
        widgets = {
            'titulo': forms.TextInput(attrs=BASE_WIDGETS),
            'descricao': forms.Textarea(attrs={**BASE_WIDGETS, 'rows': 3}),
            'sala': forms.Select(attrs=BASE_WIDGETS),
            'tipo': forms.Select(attrs=BASE_WIDGETS),
        }

    def clean_imagens(self):
        arquivos = self.files.getlist("imagens")
        return _validar_arquivos(arquivos, {"jpg", "jpeg", "png"}, MAX_IMAGE_SIZE)

    def clean_videos(self):
        arquivos = self.files.getlist("videos")
        return _validar_arquivos(arquivos, {"mp4"}, MAX_VIDEO_SIZE)

class AnomaliaFilterForm(forms.Form):
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        empty_label="Todas as Salas",
        widget=forms.Select(attrs=BASE_WIDGETS)
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos os Estados')] + Anomalia.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs=BASE_WIDGETS)
    )

class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Anomalia
        fields = ['observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={**BASE_WIDGETS, 'rows': 4, 'placeholder': 'Escreva sua observação aqui...'}),
        }

class FiltroHistoricoForm(forms.Form):
    data_resolvida = forms.DateField(required=False, label='Data de Resolução',
                                     widget=forms.DateInput(attrs={'type': 'date', **BASE_WIDGETS}))
    sala = forms.ModelChoiceField(queryset=Sala.objects.all(), required=False, label='Sala', widget=forms.Select(attrs=BASE_WIDGETS))
    computador = forms.ModelChoiceField(queryset=Computador.objects.all(), required=False, label='Computador', widget=forms.Select(attrs=BASE_WIDGETS))
