from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from anomalias.models import Anomalia
from users.access import filter_anomalias_for_user


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("nova_anomalia", "Nova Anomalia"),
        ("anomalia_atualizada", "Anomalia Atualizada"),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    @staticmethod
    def unread_count(user):
        notifications = Notification.objects.filter(recipient=user, is_read=False)
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
        return (visible_notifications | other_notifications).count()
