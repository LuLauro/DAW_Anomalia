from django.db import models


class Sala(models.Model):
    numero = models.CharField(max_length=10)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"Sala {self.numero}"
