from datetime import datetime, timedelta
from io import BytesIO
import base64

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import get_template
from django.utils import timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xhtml2pdf import pisa

from anomalias.models import Anomalia
from salas.models import Sala


def _user_can_access(user):
    return user.groups.filter(name__in=["Administrador", "Coordenador", "Tecnico"]).exists()


def _periodo_datas(periodo, data_inicio_raw, data_fim_raw):
    hoje = timezone.localdate()
    if periodo == "ultima_semana":
        inicio = hoje - timedelta(days=7)
        fim = hoje
    elif periodo == "intervalo":
        try:
            inicio = datetime.strptime(data_inicio_raw, "%Y-%m-%d").date()
            fim = datetime.strptime(data_fim_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None, None
        if inicio > fim:
            return None, None
    else:
        # semana_atual
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    return inicio, fim


def _tempo_medio_resolucao(anomalias):
    duracoes = []
    for anomalia in anomalias:
        if anomalia.data_resolvida:
            duracoes.append(anomalia.data_resolvida - anomalia.data_registo)
    if not duracoes:
        return "N/A"
    media = sum(duracoes, timedelta()) / len(duracoes)
    dias = media.days
    horas = media.seconds // 3600
    return f"{dias}d {horas}h"


def _percent(valor, total):
    if total <= 0:
        return 0
    return round((valor / total) * 100)


def grafico_estado_base64(resolvidas, pendentes, em_resolucao):
    labels = ["Resolvidas", "Pendentes", "Em resolucao"]
    valores = [resolvidas, pendentes, em_resolucao]
    cores = ["#2e7d32", "#f9a825", "#0288d1"]

    fig, ax = plt.subplots(figsize=(4.2, 3.2), dpi=120)
    ax.pie(
        valores,
        labels=labels,
        colors=cores,
        startangle=90,
        wedgeprops={"width": 0.45},
        autopct="%1.0f%%",
    )
    ax.set_title("Estado das anomalias", fontsize=11)
    ax.axis("equal")

    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def grafico_top_salas_base64(top_salas):
    labels = []
    valores = []
    for item in top_salas:
        sala = item.get("sala__numero") or item.get("computador__sala__numero") or "-"
        labels.append(str(sala))
        valores.append(item.get("total", 0))

    fig, ax = plt.subplots(figsize=(4.8, 3.0), dpi=120)
    ax.bar(labels, valores, color="#546e7a")
    ax.set_title("Top salas", fontsize=11)
    ax.set_ylabel("N de anomalias")
    ax.tick_params(axis="x", rotation=30)

    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def grafico_top_tipos_base64(top_tipos):
    labels = []
    valores = []
    for item in top_tipos:
        labels.append(item.get("tipo") or "-")
        valores.append(item.get("total", 0))

    fig, ax = plt.subplots(figsize=(4.8, 3.0), dpi=120)
    ax.bar(labels, valores, color="#8e24aa")
    ax.set_title("Top tipos", fontsize=11)
    ax.set_ylabel("N de anomalias")
    ax.tick_params(axis="x", rotation=30)

    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@login_required
def relatorio_form(request):
    if not _user_can_access(request.user):
        messages.error(request, "Acesso restrito a Administrador, Coordenador ou Tecnico.")
        return redirect("anomalias:lista_anomalias")

    salas = Sala.objects.order_by("numero")
    context = {
        "salas": salas,
        "estado_choices": Anomalia.ESTADO_CHOICES,
        "tipo_choices": Anomalia._meta.get_field("tipo").choices,
    }
    return render(request, "relatorios/relatorio_form.html", context)


@login_required
def gerar_relatorio_pdf(request):
    if not _user_can_access(request.user):
        messages.error(request, "Acesso restrito a Administrador, Coordenador ou Tecnico.")
        return redirect("anomalias:lista_anomalias")

    periodo = request.GET.get("periodo", "semana_atual")
    data_inicio_raw = request.GET.get("data_inicio")
    data_fim_raw = request.GET.get("data_fim")
    inicio, fim = _periodo_datas(periodo, data_inicio_raw, data_fim_raw)

    if not inicio or not fim:
        messages.error(request, "Intervalo de datas invalido.")
        return redirect("relatorios:form")

    filtros = Q(ativo=True, data_registo__date__range=(inicio, fim))

    sala_id = request.GET.get("sala")
    if sala_id:
        filtros &= Q(sala_id=sala_id) | Q(computador__sala_id=sala_id)

    estado = request.GET.get("estado")
    if estado:
        filtros &= Q(estado=estado)

    tipo = request.GET.get("tipo")
    if tipo:
        filtros &= Q(tipo=tipo)

    anomalias = (
        Anomalia.objects.filter(filtros)
        .select_related("computador", "sala", "reportado_por")
        .order_by("-data_registo")
    )

    total_anomalias = anomalias.count()
    total_resolvidas = anomalias.filter(estado="RESOLVIDO").count()
    total_pendentes = anomalias.filter(estado="PENDENTE").count()
    tempo_medio = _tempo_medio_resolucao(anomalias)

    is_coordenador = request.user.groups.filter(name="Coordenador").exists()
    context = {
        "instituicao_nome": "Instituicao de Ensino",
        "data_geracao": timezone.now(),
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "total_anomalias": total_anomalias,
        "total_resolvidas": total_resolvidas,
        "total_pendentes": total_pendentes,
        "tempo_medio_resolucao": tempo_medio,
        "anomalias": anomalias,
        "mostrar_reportado_por": not is_coordenador,
        "mostrar_observacoes": False,
    }

    template = get_template("relatorios/relatorio_pdf.html")
    html = template.render(context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=relatorio_anomalias.pdf"

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: # type: ignore
        messages.error(request, "Nao foi possivel gerar o PDF.")
        return redirect("relatorios:form")

    messages.success(request, "Relatorio gerado com sucesso.")
    return response


@login_required
def relatorio_semanal_pdf(request):
    if not _user_can_access(request.user):
        messages.error(request, "Acesso restrito a Administrador, Coordenador ou Tecnico.")
        return redirect("anomalias:lista_anomalias")

    # Semana atual (segunda a domingo).
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)

    anomalias = (
        Anomalia.objects.filter(ativo=True, data_registo__date__range=(inicio, fim))
        .select_related("computador", "sala", "reportado_por", "computador__sala")
        .order_by("-data_registo")
    )

    total_anomalias = anomalias.count()
    total_resolvidas = anomalias.filter(estado="RESOLVIDO").count()
    total_pendentes = anomalias.filter(estado="PENDENTE").count()
    total_em_resolucao = anomalias.filter(estado="EM_RESOLUCAO").count()
    tempo_medio = _tempo_medio_resolucao(anomalias)

    por_estado = (
        anomalias.values("estado")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    top_salas = (
        anomalias.values("sala__numero", "computador__sala__numero")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    top_tipos = (
        anomalias.values("tipo")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    is_admin = request.user.groups.filter(name="Administrador").exists()
    is_coordenador = request.user.groups.filter(name="Coordenador").exists()
    is_tecnico = request.user.groups.filter(name="Tecnico").exists()

    context = {
        "instituicao_nome": "Instituicao de Ensino",
        "data_geracao": timezone.now(),
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "total_anomalias": total_anomalias,
        "total_resolvidas": total_resolvidas,
        "total_pendentes": total_pendentes,
        "total_em_resolucao": total_em_resolucao,
        "tempo_medio_resolucao": tempo_medio,
        "percent_resolvidas": _percent(total_resolvidas, total_anomalias),
        "percent_pendentes": _percent(total_pendentes, total_anomalias),
        "anomalias": anomalias,
        "anomalias_pendentes": anomalias.filter(
            estado__in=["PENDENTE", "EM_RESOLUCAO"]
        ),
        "por_estado": por_estado,
        "top_salas": top_salas,
        "top_tipos": top_tipos,
        "is_admin": is_admin,
        "is_coordenador": is_coordenador,
        "is_tecnico": is_tecnico,
        "grafico_estado_img": grafico_estado_base64(
            total_resolvidas, total_pendentes, total_em_resolucao
        ),
        "grafico_top_salas_img": grafico_top_salas_base64(top_salas),
        "grafico_top_tipos_img": grafico_top_tipos_base64(top_tipos),
    }

    template = get_template("relatorios/relatorio_semanal_pdf.html")
    html = template.render(context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=relatorio_semanal.pdf"

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: # type: ignore
        messages.error(request, "Nao foi possivel gerar o PDF semanal.")
        return redirect("relatorios:form")

    return response
