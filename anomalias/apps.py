
from django.apps import AppConfig


class AnomaliasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'anomalias'

    def ready(self):
        import anomalias.signals
