from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

from salas.models import Sala


class PerfilCoordenador(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_coordenador",
        verbose_name="coordenador",
    )
    salas = models.ManyToManyField(
        Sala,
        blank=True,
        related_name="perfis_coordenador",
        verbose_name="salas",
    )

    class Meta:
        verbose_name = "Perfil de coordenador"
        verbose_name_plural = "Perfis de coordenador"

    def __str__(self):
        return self.user.get_username()


def _sync_coordinator_rooms(profile):
    selected_ids = set(profile.salas.values_list("pk", flat=True))
    through_model = PerfilCoordenador.salas.through

    if selected_ids:
        through_model.objects.filter(sala_id__in=selected_ids).exclude(
            perfilcoordenador_id=profile.pk
        ).delete()
        Sala.objects.filter(pk__in=selected_ids).exclude(
            coordinator=profile.user
        ).update(coordinator=profile.user)

    user_rooms = Sala.objects.filter(coordinator=profile.user)
    if selected_ids:
        user_rooms.exclude(pk__in=selected_ids).update(coordinator=None)
    else:
        user_rooms.update(coordinator=None)


@receiver(m2m_changed, sender=PerfilCoordenador.salas.through)
def sync_profile_rooms(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        _sync_coordinator_rooms(instance)


@receiver(post_delete, sender=PerfilCoordenador)
def clear_profile_rooms(sender, instance, **kwargs):
    Sala.objects.filter(coordinator=instance.user).update(coordinator=None)
