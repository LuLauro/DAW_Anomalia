from django.db.models import Q


def _has_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def _is_coordenador(user):
    return _has_group(user, "Coordenador")


def _is_professor(user):
    return _has_group(user, "Professor")


def filter_salas_for_user(queryset, user):
    if _is_coordenador(user):
        return queryset.filter(coordinator=user)
    return queryset


def filter_computadores_for_user(queryset, user):
    if _is_coordenador(user):
        return queryset.filter(sala__coordinator=user)
    return queryset


def filter_anomalias_for_user(queryset, user):
    if _is_professor(user):
        return queryset.filter(reportado_por=user)
    if _is_coordenador(user):
        return queryset.filter(
            Q(sala__coordinator=user) | Q(computador__sala__coordinator=user)
        )
    return queryset
