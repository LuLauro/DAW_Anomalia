from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from auditoria.services import log_action


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_action(
        request=request,
        user=user,
        action="LOGIN",
        entity="Autenticação",
        description=f"Login efetuado por {user.username}.",
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user is None:
        return

    log_action(
        request=request,
        user=user,
        action="LOGOUT",
        entity="Autenticação",
        description=f"Logout efetuado por {user.username}.",
    )

