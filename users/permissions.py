from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from users.access import filter_anomalias_for_user


def has_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or has_group(user, "Administrador")
    )


def is_tecnico(user):
    return user.is_authenticated and has_group(user, "Tecnico")


def is_professor(user):
    return user.is_authenticated and has_group(user, "Professor")


def is_coordenador(user):
    return user.is_authenticated and has_group(user, "Coordenador")


def can_access_computadores(user):
    return user.is_authenticated and (
        user.is_staff
        or is_admin(user)
        or is_tecnico(user)
        or is_coordenador(user)
    )


def can_view_anomalia(user, anomalia):
    if is_admin(user) or is_tecnico(user):
        return True

    if not user.is_authenticated:
        return False

    return filter_anomalias_for_user(
        anomalia.__class__.objects.filter(pk=anomalia.pk), user
    ).exists()


def is_tecnico_or_admin(user):
    return is_tecnico(user) or is_admin(user)


def can_change_estado(user, anomalia):
    return is_admin(user) or is_tecnico(user)


def can_add_observacao(user, anomalia):
    return can_view_anomalia(user, anomalia) and (
        is_admin(user) or is_tecnico(user) or is_coordenador(user)
    )


def can_delete_anomalia(user, anomalia):
    return is_admin(user) and anomalia.estado == "RESOLVIDO"


def group_required(
    check_func,
    error_message="Não tem permissão para aceder a esta página.",
    redirect_to="anomalias:lista_anomalias",
):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not check_func(request.user):
                messages.error(request, error_message)
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
