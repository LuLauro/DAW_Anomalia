from django import template
from notificacoes.models import Notification

register = template.Library()

@register.simple_tag
def get_unread_notifications_count(user):
    return Notification.unread_count(user)


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
