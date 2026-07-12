from __future__ import annotations

from django.db import OperationalError, ProgrammingError

from auditoria.models import LogAuditoria


def get_client_ip(request):
    if request is None:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None

    return request.META.get("REMOTE_ADDR")


def build_entity_label(entity):
    if entity is None:
        return "-"
    if isinstance(entity, str):
        return entity
    return getattr(entity._meta, "verbose_name", entity.__class__.__name__).title()


def build_entity_id(entity):
    if entity is None:
        return ""
    if isinstance(entity, str):
        return ""
    entity_id = getattr(entity, "pk", "")
    return str(entity_id or "")


def log_action(
    *,
    request=None,
    user=None,
    action,
    entity,
    description,
    entity_id=None,
):
    if not user and request is not None:
        user = getattr(request, "user", None)
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None

    resolved_entity_id = entity_id if entity_id is not None else build_entity_id(entity)

    try:
        return LogAuditoria.objects.create(
            utilizador=user,
            acao=action,
            entidade=build_entity_label(entity),
            entidade_id=str(resolved_entity_id or ""),
            descricao=description,
            endereco_ip=get_client_ip(request),
        )
    except (ProgrammingError, OperationalError):
        return None
