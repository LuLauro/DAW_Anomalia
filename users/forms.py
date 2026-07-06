from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


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
