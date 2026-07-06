# ai_agent/tools.py

from django.db.models import Count
from anomalias.models import Anomalia


def get_total_anomalias():
    """Total de anomalias ativas."""
    return Anomalia.objects.filter(ativo=True).count()


def get_pendentes():
    """Total de anomalias pendentes."""
    return Anomalia.objects.filter(
        ativo=True,
        estado="PENDENTE"
    ).count()


def get_em_resolucao():
    """Total de anomalias em resolução."""
    return Anomalia.objects.filter(
        ativo=True,
        estado="EM_RESOLUCAO"
    ).count()


def get_resolvidas():
    """Total de anomalias resolvidas."""
    return Anomalia.objects.filter(
        ativo=True,
        estado="RESOLVIDO"
    ).count()


def get_anomalia_mais_antiga():
    """Anomalia mais antiga ainda ativa."""

    anomalia = (
        Anomalia.objects
        .filter(ativo=True)
        .order_by("data_registo")
        .select_related("sala", "computador")
        .first()
    )

    if not anomalia:
        return None

    return {
        "id": anomalia.id,
        "titulo": anomalia.titulo,
        "estado": anomalia.estado,
        "data": anomalia.data_registo.strftime("%d/%m/%Y"),
    }


def get_ultimas_anomalias(limite=5):
    """Últimas anomalias registadas."""

    anomalias = (
        Anomalia.objects
        .filter(ativo=True)
        .order_by("-data_registo")[:limite]
    )

    resultado = []

    for a in anomalias:
        resultado.append({
            "id": a.id,
            "titulo": a.titulo,
            "estado": a.estado,
            "data": a.data_registo.strftime("%d/%m/%Y"),
        })

    return resultado


def get_sala_com_mais_ocorrencias():
    """Sala com maior número de anomalias."""

    sala = (
        Anomalia.objects
        .filter(
            ativo=True,
            sala__isnull=False
        )
        .values("sala__numero")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    return sala


def get_computador_com_mais_ocorrencias():
    """Computador com maior número de anomalias."""

    computador = (
        Anomalia.objects
        .filter(
            ativo=True,
            computador__isnull=False
        )
        .values("computador__numero_identificacao")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    return computador