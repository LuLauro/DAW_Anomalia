from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from computadores.models import Computador
from salas.models import Sala

TIPO_CHOICES = [
    ("MOBILARIO", "Mobiliário"),
    ("SALA", "Problema na Sala"),
    ("LIMPEZA", "Limpeza"),
    ("PROJETOR", "Projetor com Problema"),
    ("ACESSO", "Acesso Restrito ou Trancado"),
    ("REDE", "Rede ou Internet"),
    ("OUTRO", "Outro"),
]


class Anomalia(models.Model):
    ESTADO_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("EM_RESOLUCAO", "Em Resolução"),
        ("RESOLVIDO", "Resolvido"),
    ]
    PRIORIDADE_CHOICES = [
        ("CRITICA", "Crítica"),
        ("ALTA", "Alta"),
        ("MEDIA", "Média"),
        ("BAIXA", "Baixa"),
    ]

    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    data_registo = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="PENDENTE")
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default="MEDIA",
    )
    computador = models.ForeignKey(
        Computador,
        on_delete=models.CASCADE,
        related_name="anomalias",
        blank=True,
        null=True,
    )
    sala = models.ForeignKey(
        Sala,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anomalias",
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, blank=True, null=True)
    reportado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    observacoes = models.TextField(blank=True, null=True)
    data_resolvida = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.titulo} ({self.estado})"

    def clean(self):
        super().clean()
        if not self.prioridade:
            raise ValidationError({"prioridade": "A prioridade é obrigatória."})

        if self.pk:
            original = Anomalia.objects.filter(pk=self.pk).only("estado", "prioridade").first()
            if (
                original
                and original.estado == "RESOLVIDO"
                and original.prioridade != self.prioridade
            ):
                raise ValidationError(
                    {"prioridade": "A prioridade não pode ser alterada depois da resolução."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def marcar_resolvido(self):
        self.estado = "RESOLVIDO"
        self.data_resolvida = now()
        self.save()

    def adicionar_observacao(self, texto):
        if self.observacoes:
            self.observacoes += f"\n{texto}"
        else:
            self.observacoes = texto
        self.save()


class AnexoAnomalia(models.Model):
    TIPO_CHOICES = [
        ("IMAGEM", "Imagem"),
        ("VIDEO", "Video"),
    ]

    anomalia = models.ForeignKey(
        Anomalia, on_delete=models.CASCADE, related_name="anexos"
    )
    arquivo = models.FileField(upload_to="anomalias/anexos/")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.anomalia.titulo} - {self.tipo}"


class Perfil(models.Model):
    TIPO_CHOICES = [
        ("PROF", "Professor"),
        ("COORD", "Coordenador"),
        ("ADMIN", "Administrador"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    def __str__(self):
        tipo_display = getattr(self, "get_tipo_display", lambda: self.tipo)()
        return f"{self.user.username} - {tipo_display}"
