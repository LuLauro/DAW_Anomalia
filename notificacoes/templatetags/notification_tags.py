from django import template
from notificacoes.models import Notification
from users.permissions import can_access_computadores

register = template.Library()

@register.simple_tag
def get_unread_notifications_count(user):
    return Notification.unread_count(user)


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.filter(name='can_access_computadores')
def can_access_computadores_filter(user):
    return can_access_computadores(user)
