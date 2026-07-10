import os
import random
from datetime import timedelta

import django
from django.utils import timezone

# ALTERA ESTA LINHA para o nome do teu projeto
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django.setup()

from django.contrib.auth.models import User
from anomalias.models import Anomalia, AnexoAnomalia
from computadores.models import Computador

print("=== Limpeza da base de dados ===")

# Apaga anexos e depois anomalias
AnexoAnomalia.objects.all().delete()
Anomalia.objects.all().delete()

print("Anomalias antigas removidas.")

titulos = [
    "Computador não liga",
    "Monitor sem imagem",
    "Monitor com linhas",
    "Monitor partido",
    "Teclado avariado",
    "Rato não funciona",
    "Computador muito lento",
    "Computador reinicia sozinho",
    "Internet indisponível",
    "Ligação de rede instável",
    "Projetor sem sinal",
    "Projetor desfocado",
    "Colunas sem som",
    "Mesa instável",
    "Mesa sem borracha no pé",
    "Cadeira partida",
    "Tomada sem energia",
    "Windows bloqueado",
    "Software não abre",
    "Impressora não imprime",
    "Ventoinha com muito ruído",
    "Ecrã partido",
    "Cabo HDMI danificado",
]

descricoes = [
    "O problema foi identificado durante uma aula.",
    "O equipamento necessita de intervenção técnica.",
    "O problema mantém-se após reiniciar o computador.",
    "Foi reportado por vários utilizadores.",
    "O equipamento apresenta falhas frequentes.",
    "Foi efetuado um teste básico sem sucesso.",
    "A avaria impede a utilização normal do equipamento.",
]

ESTADOS = [
    ("PENDENTE", 45),
    ("EM_RESOLUCAO", 30),
    ("RESOLVIDO", 25),
]

PRIORIDADES = [
    ("CRITICA", 10),
    ("ALTA", 25),
    ("MEDIA", 45),
    ("BAIXA", 20),
]

computadores = list(
    Computador.objects.select_related("sala").all()
)

professores = list(
    User.objects.filter(groups__name="Professor").distinct()
)

if not computadores:
    raise Exception("Não existem computadores na base de dados.")

if not professores:
    raise Exception("Não existem professores na base de dados.")

print(f"Computadores encontrados: {len(computadores)}")
print(f"Professores encontrados: {len(professores)}")

for _ in range(35):

    computador = random.choice(computadores)

    estado = random.choices(
        [x[0] for x in ESTADOS],
        weights=[x[1] for x in ESTADOS],
    )[0]

    prioridade = random.choices(
        [x[0] for x in PRIORIDADES],
        weights=[x[1] for x in PRIORIDADES],
    )[0]

    data_registo = timezone.now() - timedelta(
        days=random.randint(1, 120)
    )

    anomalia = Anomalia.objects.create(
        titulo=random.choice(titulos),
        descricao=random.choice(descricoes),
        prioridade=prioridade,
        estado=estado,
        computador=computador,
        sala=computador.sala,
        reportado_por=random.choice(professores),
        data_registo=data_registo,
        ativo=True,
    )

    if estado == "RESOLVIDO":
        anomalia.data_resolvida = (
            data_registo + timedelta(days=random.randint(1, 10))
        )
        anomalia.save(update_fields=["data_resolvida"])

print("\n================================")
print("35 anomalias criadas com sucesso!")
print("================================")