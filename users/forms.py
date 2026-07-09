from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db import transaction

from anomalias.models import Perfil

from .models import PerfilCoordenador

PROFILE_GROUP_CHOICES = [
    ("Administrador", "Administrador"),
    ("Professor", "Professor"),
    ("Coordenador", "Coordenador"),
    ("Tecnico", "Técnico"),
]
PROFILE_TYPE_MAP = {
    "Administrador": "ADMIN",
    "Professor": "PROF",
    "Coordenador": "COORD",
    "Tecnico": "TEC",
}


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark text-light border-primary',
        'placeholder': 'Nome de utilizador'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-dark text-light border-primary',
        'placeholder': 'Palavra-passe'
    }))


class SignUpForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nome de utilizador'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email'
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Palavra-passe'
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirmar palavra-passe'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


def _split_full_name(full_name):
    parts = (full_name or "").strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def sync_user_profile(user, perfil):
    group_names = [choice[0] for choice in PROFILE_GROUP_CHOICES]
    groups = {
        name: Group.objects.get_or_create(name=name)[0]
        for name in group_names
    }
    user.groups.set([groups[perfil]])

    user.is_staff = perfil == "Administrador"
    user.save(update_fields=["is_staff"])

    perfil_tipo = PROFILE_TYPE_MAP.get(perfil)
    if perfil_tipo:
        perfil_obj, _ = Perfil.objects.get_or_create(
            user=user, defaults={"tipo": perfil_tipo}
        )
        if perfil_obj.tipo != perfil_tipo:
            perfil_obj.tipo = perfil_tipo
            perfil_obj.save(update_fields=["tipo"])

    if perfil == "Coordenador":
        PerfilCoordenador.objects.get_or_create(user=user)
    else:
        PerfilCoordenador.objects.filter(user=user).delete()


def get_user_profile_display(user):
    first_group = user.groups.order_by("name").first()
    if not first_group:
        return "-"
    if first_group.name == "Tecnico":
        return "Técnico"
    return first_group.name


class UserSearchForm(forms.Form):
    pesquisa = forms.CharField(
        required=False,
        label="Pesquisar",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Pesquisar por nome ou nome de utilizador",
            }
        ),
    )


class BaseUserManagementForm(forms.Form):
    nome = forms.CharField(
        label="Nome",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nome completo"}
        ),
    )
    username = forms.CharField(
        label="Nome de utilizador",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nome de utilizador"}
        ),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
    )
    perfil = forms.ChoiceField(
        label="Perfil",
        choices=PROFILE_GROUP_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    estado = forms.ChoiceField(
        label="Estado",
        choices=[("ativo", "Ativo"), ("inativo", "Inativo")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user_instance=None, **kwargs):
        self.user_instance = user_instance
        super().__init__(*args, **kwargs)
        if user_instance is not None:
            self.fields["nome"].initial = user_instance.get_full_name() or user_instance.first_name
            self.fields["username"].initial = user_instance.username
            self.fields["email"].initial = user_instance.email
            self.fields["perfil"].initial = next(
                (
                    choice[0]
                    for choice in PROFILE_GROUP_CHOICES
                    if user_instance.groups.filter(name=choice[0]).exists()
                ),
                "Professor",
            )
            self.fields["estado"].initial = "ativo" if user_instance.is_active else "inativo"

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        queryset = User.objects.filter(username__iexact=username)
        if self.user_instance is not None:
            queryset = queryset.exclude(pk=self.user_instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Já existe um utilizador com esse nome de utilizador.")
        return username

    def save_common_fields(self, user):
        first_name, last_name = _split_full_name(self.cleaned_data["nome"])
        user.first_name = first_name
        user.last_name = last_name
        user.username = self.cleaned_data["username"]
        user.email = self.cleaned_data.get("email", "").strip()
        user.is_active = self.cleaned_data["estado"] == "ativo"
        return user


class UserCreateForm(BaseUserManagementForm):
    password = forms.CharField(
        label="Palavra-passe",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Palavra-passe"}
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar palavra-passe",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirmar palavra-passe"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if not password:
            self.add_error("password", "A palavra-passe é obrigatória.")
        if not confirm_password:
            self.add_error("confirm_password", "A confirmação da palavra-passe é obrigatória.")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "As palavras-passe não coincidem.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=(self.cleaned_data.get("email") or "").strip(),
            password=self.cleaned_data["password"],
        )
        user = self.save_common_fields(user)
        user.save(update_fields=["first_name", "last_name", "username", "email", "is_active"])
        sync_user_profile(user, self.cleaned_data["perfil"])
        return user


class UserUpdateForm(BaseUserManagementForm):
    password = forms.CharField(
        label="Nova palavra-passe",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Deixe vazio para manter"}
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar nova palavra-passe",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirme a nova palavra-passe"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and password != confirm_password:
            self.add_error("confirm_password", "As palavras-passe não coincidem.")
        if confirm_password and not password:
            self.add_error("password", "Indique a nova palavra-passe para a poder confirmar.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        user = self.save_common_fields(self.user_instance)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        user.save()
        sync_user_profile(user, self.cleaned_data["perfil"])
        return user
