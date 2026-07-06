from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render

from anomalias.models import Anomalia
from users.access import filter_anomalias_for_user

from .models import Notification


def _notifications_for_user(user):
    notifications = Notification.objects.filter(recipient=user)
    anomalia_content_type = ContentType.objects.get_for_model(Anomalia)
    visible_anomalia_ids = filter_anomalias_for_user(
        Anomalia.objects.all(),
        user,
    ).values("id")
    visible_notifications = notifications.filter(
        content_type=anomalia_content_type,
        object_id__in=visible_anomalia_ids,
    )
    other_notifications = notifications.exclude(content_type=anomalia_content_type)
    return visible_notifications | other_notifications


@login_required
def notification_list(request):
    notifications = _notifications_for_user(request.user).order_by("-created_at")
    return render(
        request,
        "notificacoes/notification_list.html",
        {"notifications": notifications},
    )


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        _notifications_for_user(request.user),
        id=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save()
    return redirect("notificacoes:list")


@login_required
def mark_all_as_read(request):
    _notifications_for_user(request.user).filter(is_read=False).update(is_read=True)
    messages.success(request, "Todas as notificações foram marcadas como lidas.")
    return redirect("notificacoes:list")
