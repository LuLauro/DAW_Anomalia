from django.db import models
from salas.models import Sala


class Computador(models.Model):
    numero_identificacao = models.CharField(max_length=20)
    sala = models.ForeignKey(
        Sala, on_delete=models.CASCADE, related_name='computadores')
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    data_aquisicao = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"PC {self.numero_identificacao} - Sala {self.sala.numero}"

    class Meta:
        verbose_name_plural = "Computadores"
