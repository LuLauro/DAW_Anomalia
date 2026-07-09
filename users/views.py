from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from users.permissions import is_admin, is_coordenador, is_professor, is_tecnico

from .forms import (
    LoginForm,
    SignUpForm,
    UserCreateForm,
    UserSearchForm,
    UserUpdateForm,
    get_user_profile_display,
)
from django.contrib.auth.decorators import user_passes_test


def _user_home_url(user):
    if is_admin(user):
        return reverse("dashboard:index")
    if is_tecnico(user):
        return reverse("tecnico:dashboard")
    if is_coordenador(user):
        return reverse("dashboard:coordinator")
    return reverse("anomalias:lista_anomalias")


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(
                request, "Não tem permissão para aceder à gestão de utilizadores."
            )
            return redirect(_user_home_url(request.user))
        return view_func(request, *args, **kwargs)

    return _wrapped_view

@login_required
@user_passes_test(is_tecnico)
def dashboard_tecnico(request):
    return render(request, 'tecnico/dashboard.html')
        
class CustomLoginView(LoginView):
        authentication_form = LoginForm
        template_name = 'users/login.html'

        def get_success_url(self):
            user = self.request.user

            if is_admin(user):
                return '/dashboard/'
            elif is_tecnico(user):
                return '/tecnico/dashboard/'
            elif is_professor(user):
                return '/anomalias/'
            elif is_coordenador(user):
                return '/dashboard/coordenador/'
            else:
                return '/'
    

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('users:login') # vai para login customizado

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('anomalias:lista_anomalias')
    else:
        form = SignUpForm()
    return render(request, 'users/signup.html', {'form': form})


@admin_required
def lista_utilizadores(request):
    search_form = UserSearchForm(request.GET or None)
    utilizadores = User.objects.all().prefetch_related("groups").order_by("-date_joined", "username")

    if search_form.is_valid():
        pesquisa = (search_form.cleaned_data.get("pesquisa") or "").strip()
        if pesquisa:
            utilizadores = utilizadores.filter(
                Q(username__icontains=pesquisa)
                | Q(first_name__icontains=pesquisa)
                | Q(last_name__icontains=pesquisa)
            )
    else:
        pesquisa = ""

    paginator = Paginator(utilizadores, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    for utilizador in page_obj.object_list:
        utilizador.perfil_label = get_user_profile_display(utilizador)

    return render(
        request,
        "users/lista_utilizadores.html",
        {
            "search_form": search_form,
            "page_obj": page_obj,
            "utilizadores": page_obj.object_list,
            "pesquisa": pesquisa,
        },
    )


@admin_required
def novo_utilizador(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilizador criado com sucesso.")
            return redirect("user_management:lista_utilizadores")
        messages.error(request, "Não foi possível criar o utilizador.")
    else:
        form = UserCreateForm(initial={"estado": "ativo", "perfil": "Professor"})

    return render(
        request,
        "users/form_utilizador.html",
        {
            "form": form,
            "page_title": "Novo Utilizador",
            "submit_label": "Criar utilizador",
            "is_edit": False,
        },
    )


@admin_required
def editar_utilizador(request, user_id):
    utilizador = get_object_or_404(User.objects.prefetch_related("groups"), pk=user_id)

    if request.method == "POST":
        form = UserUpdateForm(request.POST, user_instance=utilizador)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilizador atualizado com sucesso.")
            return redirect("user_management:lista_utilizadores")
        messages.error(request, "Não foi possível atualizar o utilizador.")
    else:
        form = UserUpdateForm(user_instance=utilizador)

    return render(
        request,
        "users/form_utilizador.html",
        {
            "form": form,
            "page_title": "Editar Utilizador",
            "submit_label": "Guardar alterações",
            "is_edit": True,
            "utilizador": utilizador,
        },
    )


@admin_required
def alterar_estado_utilizador(request, user_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    utilizador = get_object_or_404(User, pk=user_id)
    utilizador.is_active = not utilizador.is_active
    utilizador.save(update_fields=["is_active"])

    estado = "ativado" if utilizador.is_active else "desativado"
    messages.success(request, f"Utilizador {estado} com sucesso.")
    return redirect("user_management:lista_utilizadores")
