from django.db.models.signals import post_save
from django.dispatch import receiver
from anomalias.models import Anomalia
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

@receiver(post_save, sender=Anomalia)
def criar_notificacao_anomalia(sender, instance, created, **kwargs):
    tipo = None
    if created:
        tipo = 'nova_anomalia'
        titulo = 'Nova Anomalia Registrada'
        mensagem = f'Anomalia "{instance.titulo}" foi registrada.'
    elif instance.estado in ['EM_RESOLUCAO', 'RESOLVIDO']:
        tipo = 'anomalia_atualizada'
        titulo = f'Anomalia {instance.estado.capitalize()}'
        mensagem = f'A anomalia "{instance.titulo}" foi atualizada para "{instance.get_estado_display()}".'

    if tipo:
        content_type = ContentType.objects.get_for_model(instance)

        grupos_destino = ['Administrador', 'Coordenador']
        destinatarios = User.objects.filter(groups__name__in=grupos_destino)

        for user in destinatarios:
            Notification.objects.create(
                recipient=user,
                notification_type=tipo,
                title=titulo,
                message=mensagem,
                content_type=content_type,
                object_id=instance.id
            )
