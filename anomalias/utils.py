from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string

from users.permissions import is_admin, is_coordenador, is_professor, is_tecnico

User = get_user_model()


def _room_for_anomaly(anomalia):
    if getattr(anomalia, "sala", None):
        return anomalia.sala
    computador = getattr(anomalia, "computador", None)
    return getattr(computador, "sala", None)


def _admin_users():
    return User.objects.filter(
        Q(is_staff=True) | Q(groups__name="Administrador")
    ).distinct()


def _coordinator_users_for_room(room):
    if room is None:
        return User.objects.none()

    coordinator_ids = set()

    coordinator = getattr(room, "coordinator", None)
    if coordinator is not None:
        coordinator_ids.add(coordinator.pk)

    profile_relation = getattr(room, "perfis_coordenador", None)
    if profile_relation is not None:
        coordinator_ids.update(
            profile_relation.values_list("user_id", flat=True)
        )

    if not coordinator_ids:
        return User.objects.none()

    return User.objects.filter(pk__in=coordinator_ids).distinct()


def _unique_emails(users, exclude_users=None):
    excluded_ids = {
        user.pk for user in (exclude_users or []) if getattr(user, "pk", None)
    }
    emails = []
    seen = set()

    for user in users.distinct():
        if user.pk in excluded_ids:
            continue
        email = (getattr(user, "email", "") or "").strip()
        if not email or email in seen:
            continue
        seen.add(email)
        emails.append(email)

    return emails


def _combine_users(*querysets):
    user_ids = set()

    for queryset in querysets:
        if queryset is None:
            continue
        user_ids.update(queryset.values_list("pk", flat=True))

    if not user_ids:
        return User.objects.none()

    return User.objects.filter(pk__in=user_ids).distinct()


def get_email_recipients_for_new_anomaly(anomalia, actor):
    room = _room_for_anomaly(anomalia)
    admin_users = _admin_users()
    coordinator_users = _coordinator_users_for_room(room)

    if room is None:
        return _unique_emails(admin_users, exclude_users=[actor])

    if not coordinator_users.exists():
        return _unique_emails(admin_users, exclude_users=[actor])

    if is_coordenador(actor):
        recipients = admin_users
    elif is_admin(actor):
        recipients = coordinator_users
    elif is_professor(actor) or is_tecnico(actor):
        recipients = _combine_users(admin_users, coordinator_users)
    else:
        recipients = _combine_users(admin_users, coordinator_users)

    return _unique_emails(recipients, exclude_users=[actor])


def get_email_recipients_for_status_change(anomalia, actor):
    room = _room_for_anomaly(anomalia)
    recipients = _combine_users(_admin_users(), _coordinator_users_for_room(room))

    reporter = getattr(anomalia, "reportado_por", None)
    if reporter is not None and reporter.pk != getattr(actor, "pk", None):
        recipients = _combine_users(recipients, User.objects.filter(pk=reporter.pk))

    return _unique_emails(recipients, exclude_users=[actor])


def enviar_email_destinatarios(assunto, mensagem, destinatarios):
    if not destinatarios:
        return

    html_message = render_to_string(
        "notificacoes/email_template.html",
        {
            "titulo": assunto,
            "mensagem": mensagem,
            "link": "",
        },
    )
    email = EmailMultiAlternatives(
        subject=assunto,
        body=mensagem,
        from_email=settings.EMAIL_HOST_USER,
        to=list(destinatarios),
    )
    email.encoding = "utf-8"
    email.attach_alternative(html_message, "text/html; charset=utf-8")
    email.send(fail_silently=False)


def enviar_email_grupos(assunto: str, mensagem: str, grupos=None):
    grupos = grupos or ["Administrador", "Coordenador"]
    users = User.objects.filter(groups__name__in=grupos).distinct()
    enviar_email_destinatarios(assunto, mensagem, _unique_emails(users))
