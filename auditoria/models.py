from django.conf import settings
from django.db import models


class LogAuditoria(models.Model):
    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_auditoria",
    )
    acao = models.CharField(max_length=80)
    entidade = models.CharField(max_length=120)
    entidade_id = models.CharField(max_length=50, blank=True)
    descricao = models.TextField()
    endereco_ip = models.GenericIPAddressField(null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora", "-id"]
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"

    def __str__(self):
        return f"{self.acao} - {self.entidade} ({self.data_hora:%d/%m/%Y %H:%M})"

