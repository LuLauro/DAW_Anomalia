import os

from django import forms
from django.utils.datastructures import MultiValueDict

from computadores.models import Computador
from salas.models import Sala
from users.access import filter_computadores_for_user, filter_salas_for_user

from .models import Anomalia

BASE_WIDGETS = {"class": "form-control"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024


class SearchableSelect(forms.Select):
    pass


class ComputerRoomSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value:
            try:
                computador = self.choices.queryset.get(pk=value)
            except Exception:
                computador = None
            if computador is not None:
                option["attrs"]["data-room-id"] = str(computador.sala_id)
        return option


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
            raise forms.ValidationError("Tipo de ficheiro não permitido.")
        if arquivo.size > tamanho_maximo:
            raise forms.ValidationError("Tamanho de ficheiro excede o limite permitido.")
    return arquivos


class AnomaliaForm(forms.ModelForm):
    prioridade = forms.ChoiceField(
        choices=Anomalia.PRIORIDADE_CHOICES,
        initial="MEDIA",
        label="Prioridade",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.order_by("numero"),
        required=False,
        label="Sala",
        empty_label="",
        widget=SearchableSelect(
            attrs={
                **BASE_WIDGETS,
                "class": "form-select js-room-select",
                "data-tom-select": "room",
            }
        ),
    )
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
        label="Vídeos (opcional)",
    )

    class Meta:
        model = Anomalia
        fields = ["titulo", "descricao", "prioridade", "sala", "computador"]
        labels = {
            "titulo": "Título",
            "descricao": "Descrição",
            "prioridade": "Prioridade",
            "sala": "Sala",
            "computador": "Computador",
        }
        widgets = {
            "titulo": forms.TextInput(attrs=BASE_WIDGETS),
            "descricao": forms.Textarea(attrs={**BASE_WIDGETS, "rows": 3}),
            "computador": ComputerRoomSelect(
                attrs={
                    **BASE_WIDGETS,
                    "class": "form-select js-computer-select",
                    "data-tom-select": "computer",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sala"].queryset = filter_salas_for_user(
            Sala.objects.order_by("numero"), user
        )
        computadores_queryset = filter_computadores_for_user(
            Computador.objects.select_related("sala"), user
        ).order_by("sala__numero", "numero_identificacao")
        self.fields["computador"].queryset = computadores_queryset

        sala_inicial = None
        computador_atual = self.instance.computador if getattr(self.instance, "pk", None) else None
        if computador_atual:
            sala_inicial = computador_atual.sala
            self.initial.setdefault("sala", computador_atual.sala_id)
        elif getattr(self.instance, "sala_id", None):
            sala_inicial = self.instance.sala

        sala_data = self.data.get("sala") if self.is_bound else None
        computador_disponivel = False
        if sala_data:
            try:
                sala_id = int(sala_data)
            except (TypeError, ValueError):
                sala_id = None
            if sala_id:
                computador_disponivel = computadores_queryset.filter(sala_id=sala_id).exists()
        elif sala_inicial:
            computador_disponivel = computadores_queryset.filter(sala=sala_inicial).exists()

        self.fields["computador"].required = False
        if not computador_disponivel and not computador_atual:
            self.fields["computador"].widget.attrs["disabled"] = "disabled"
        else:
            self.fields["computador"].widget.attrs.pop("disabled", None)

    def clean(self):
        cleaned_data = super().clean()
        sala = cleaned_data.get("sala")
        computador = cleaned_data.get("computador")

        if computador and sala and computador.sala_id != sala.id:
            self.add_error(
                "computador",
                "O computador selecionado não pertence à sala escolhida.",
            )

        if computador and not sala:
            cleaned_data["sala"] = computador.sala

        return cleaned_data

    def clean_imagens(self):
        arquivos = self.files.getlist("imagens")
        return _validar_arquivos(arquivos, {"jpg", "jpeg", "png"}, MAX_IMAGE_SIZE)

    def clean_videos(self):
        arquivos = self.files.getlist("videos")
        return _validar_arquivos(arquivos, {"mp4"}, MAX_VIDEO_SIZE)


class AnomaliaGeralForm(forms.ModelForm):
    prioridade = forms.ChoiceField(
        choices=Anomalia.PRIORIDADE_CHOICES,
        initial="MEDIA",
        label="Prioridade",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.order_by("numero"),
        required=False,
        label="Sala",
        empty_label="",
        widget=SearchableSelect(
            attrs={
                **BASE_WIDGETS,
                "class": "form-select js-room-select",
                "data-tom-select": "room",
            }
        ),
    )
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
        label="Vídeos (opcional)",
    )

    class Meta:
        model = Anomalia
        fields = ["titulo", "descricao", "prioridade", "sala", "tipo"]
        labels = {
            "titulo": "Título",
            "descricao": "Descrição",
            "prioridade": "Prioridade",
            "sala": "Sala",
            "tipo": "Tipo",
        }
        widgets = {
            "titulo": forms.TextInput(attrs=BASE_WIDGETS),
            "descricao": forms.Textarea(attrs={**BASE_WIDGETS, "rows": 3}),
            "tipo": forms.Select(attrs=BASE_WIDGETS),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sala"].queryset = filter_salas_for_user(
            Sala.objects.order_by("numero"), user
        )

    def clean_imagens(self):
        arquivos = self.files.getlist("imagens")
        return _validar_arquivos(arquivos, {"jpg", "jpeg", "png"}, MAX_IMAGE_SIZE)

    def clean_videos(self):
        arquivos = self.files.getlist("videos")
        return _validar_arquivos(arquivos, {"mp4"}, MAX_VIDEO_SIZE)


class AnomaliaFilterForm(forms.Form):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sala"].queryset = filter_salas_for_user(
            Sala.objects.all(), user
        ).order_by("numero")

    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        empty_label="Todas as Salas",
        label="Sala",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    pesquisa = forms.CharField(
        required=False,
        label="Pesquisar",
        widget=forms.TextInput(
            attrs={**BASE_WIDGETS, "placeholder": "Título, descrição ou prioridade"}
        ),
    )
    estado = forms.ChoiceField(
        choices=[("", "Todos os Estados")] + Anomalia.ESTADO_CHOICES,
        required=False,
        label="Estado",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    prioridade = forms.ChoiceField(
        choices=[("", "Todas as Prioridades")] + Anomalia.PRIORIDADE_CHOICES,
        required=False,
        label="Prioridade",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    ordenacao = forms.ChoiceField(
        choices=[
            ("recentes", "Mais recentes"),
            ("prioridade", "Prioridade"),
        ],
        required=False,
        initial="recentes",
        label="Ordenar por",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )


class AnomaliaPrioridadeForm(forms.ModelForm):
    prioridade = forms.ChoiceField(
        choices=Anomalia.PRIORIDADE_CHOICES,
        label="Prioridade",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )

    class Meta:
        model = Anomalia
        fields = ["prioridade"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self.instance, "estado", None) == "RESOLVIDO":
            self.fields["prioridade"].disabled = True

    def clean_prioridade(self):
        prioridade = self.cleaned_data.get("prioridade")
        if self.instance.pk and self.instance.estado == "RESOLVIDO":
            return self.instance.prioridade
        if not prioridade:
            raise forms.ValidationError("A prioridade é obrigatória.")
        return prioridade


class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Anomalia
        fields = ["observacoes"]
        widgets = {
            "observacoes": forms.Textarea(
                attrs={
                    **BASE_WIDGETS,
                    "rows": 4,
                    "placeholder": "Escreva a sua observação aqui...",
                }
            ),
        }


class FiltroHistoricoForm(forms.Form):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sala"].queryset = filter_salas_for_user(
            Sala.objects.all(), user
        ).order_by("numero")
        self.fields["computador"].queryset = filter_computadores_for_user(
            Computador.objects.all(), user
        ).order_by("sala__numero", "numero_identificacao")

    data_resolvida = forms.DateField(
        required=False,
        label="Data de Resolução",
        widget=forms.DateInput(attrs={"type": "date", **BASE_WIDGETS}),
    )
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.all(),
        required=False,
        label="Sala",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
    computador = forms.ModelChoiceField(
        queryset=Computador.objects.all(),
        required=False,
        label="Computador",
        widget=forms.Select(attrs=BASE_WIDGETS),
    )
