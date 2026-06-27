from django.db import models
from django.contrib.auth.models import User


class Sala(models.Model):
    numero = models.CharField(max_length=10)
    descricao = models.TextField(blank=True)
    coordinator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salas_coordenadas",
        help_text="Coordenador responsavel por esta sala.",
    )

    def __str__(self):
        return f"Sala {self.numero}"
