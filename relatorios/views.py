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

from auditoria.services import log_action
from anomalias.qr_utils import (
    build_computador_anomalia_url,
    build_qr_code_data_uri,
    build_sala_anomalia_url,
)
from anomalias.models import Anomalia
from computadores.models import Computador
from salas.models import Sala
from users.access import filter_anomalias_for_user, filter_salas_for_user
from users.permissions import is_admin


def _user_can_access(user):
    return user.groups.filter(name__in=["Administrador", "Coordenador", "Tecnico"]).exists()


def _user_can_access_qr_kit(user):
    return is_admin(user)


def _build_qr_kit_items(request, qr_type, sala_id=None):
    salas = Sala.objects.order_by("numero")
    computadores = Computador.objects.select_related("sala").order_by(
        "sala__numero", "numero_identificacao"
    )

    if sala_id:
        salas = salas.filter(pk=sala_id)
        computadores = computadores.filter(sala_id=sala_id)

    items = []

    if qr_type in {"salas", "ambos"}:
        for sala in salas:
            target_url = build_sala_anomalia_url(request, sala.pk)
            items.append(
                {
                    "entity_type": "sala",
                    "title": f"Sala {sala.numero}",
                    "meta_lines": [f"Sala: {sala.numero}"],
                    "description": "Escaneie este cÃ³digo para reportar uma anomalia nesta sala.",
                    "target_url": target_url,
                    "qr_code_data_uri": build_qr_code_data_uri(target_url),
                }
            )

    if qr_type in {"computadores", "ambos"}:
        for computador in computadores:
            target_url = build_computador_anomalia_url(
                request,
                computador.sala_id,
                computador.pk,
            )
            items.append(
                {
                    "entity_type": "computador",
                    "title": f"Computador {computador.numero_identificacao}",
                    "meta_lines": [
                        f"Sala: {computador.sala.numero}",
                        f"Computador: {computador.numero_identificacao}",
                    ],
                    "description": "Escaneie este cÃ³digo para reportar uma anomalia neste computador.",
                    "target_url": target_url,
                    "qr_code_data_uri": build_qr_code_data_uri(target_url),
                }
            )

    return items


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


def _anomalia_relatorio_filtro_base():
    return Q(ativo=True) | Q(estado="RESOLVIDO", data_resolvida__isnull=False)


def _priority_style(prioridade):
    return {
        "CRITICA": {"bg": "#dc3545", "fg": "#ffffff", "label": "CrÃ­tica"},
        "ALTA": {"bg": "#fd7e14", "fg": "#ffffff", "label": "Alta"},
        "MEDIA": {"bg": "#ffc107", "fg": "#212529", "label": "MÃ©dia"},
        "BAIXA": {"bg": "#198754", "fg": "#ffffff", "label": "Baixa"},
    }.get(prioridade, {"bg": "#6c757d", "fg": "#ffffff", "label": prioridade or "-"})


def _attach_priority_style(anomalias):
    anomalias = list(anomalias)
    for anomalia in anomalias:
        anomalia.priority_style = _priority_style(anomalia.prioridade)
    return anomalias


def grafico_estado_base64(resolvidas, pendentes, em_resolucao):
    labels = ["Resolvidas", "Pendentes", "Em resoluÃ§Ã£o"]
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
    ax.set_ylabel("N.Âº de anomalias")
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
    ax.set_ylabel("N.Âº de anomalias")
    ax.tick_params(axis="x", rotation=30)

    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@login_required
def relatorio_form(request):
    if not _user_can_access(request.user):
        messages.error(request, "Acesso restrito a Administrador, Coordenador ou TÃ©cnico.")
        return redirect("anomalias:lista_anomalias")

    salas = filter_salas_for_user(Sala.objects.all(), request.user).order_by("numero")
    context = {
        "salas": salas,
        "estado_choices": Anomalia.ESTADO_CHOICES,
        "prioridade_choices": Anomalia.PRIORIDADE_CHOICES,
        "tipo_choices": Anomalia._meta.get_field("tipo").choices,
    }
    return render(request, "relatorios/relatorio_form.html", context)


@login_required
def qrcode_kit_form(request):
    if not _user_can_access_qr_kit(request.user):
        messages.error(request, "Acesso restrito a Administrador.")
        return redirect("anomalias:lista_anomalias")

    salas = Sala.objects.order_by("numero")
    context = {
        "salas": salas,
        "selected_type": request.GET.get("tipo", "ambos"),
        "selected_sala": request.GET.get("sala", ""),
    }
    return render(request, "relatorios/qrcode_kit_form.html", context)


@login_required
def qrcode_kit_pdf(request):
    if not _user_can_access_qr_kit(request.user):
        messages.error(request, "Acesso restrito a Administrador.")
        return redirect("anomalias:lista_anomalias")

    qr_type = request.GET.get("tipo") or "ambos"
    if qr_type not in {"salas", "computadores", "ambos"}:
        qr_type = "ambos"

    sala_id_raw = request.GET.get("sala")
    sala_id = None
    if sala_id_raw:
        try:
            sala_id = int(sala_id_raw)
        except (TypeError, ValueError):
            sala_id = None

    items = _build_qr_kit_items(request, qr_type, sala_id=sala_id)
    if not items:
        messages.warning(request, "Nenhum QR Code encontrado para os filtros selecionados.")
        return redirect("relatorios:qrcode_kit_form")

    context = {
        "items": items,
        "generated_at": timezone.now(),
    }
    log_action(
        request=request,
        action="IMPRIMIR_QR_CODES",
        entity="QR Codes",
        description=(
            f"Página de impressão de QR Codes aberta. "
            f"Tipo: {qr_type}. Sala: {sala_id or 'todas'}."
        ),
    )
    return render(request, "relatorios/qrcode_kit_pdf.html", context)


@login_required
def gerar_relatorio_pdf(request):
    if not _user_can_access(request.user):
        messages.error(
            request,
            "Acesso restrito a Administrador, Coordenador ou TÃ©cnico.",
        )
        return redirect("anomalias:lista_anomalias")

    periodo = request.GET.get("periodo", "semana_atual")
    data_inicio_raw = request.GET.get("data_inicio")
    data_fim_raw = request.GET.get("data_fim")

    inicio, fim = _periodo_datas(
        periodo,
        data_inicio_raw,
        data_fim_raw,
    )

    if not inicio or not fim:
        messages.error(request, "Intervalo de datas invÃ¡lido.")
        return redirect("relatorios:form")

    from datetime import datetime, time

    inicio_dt = timezone.make_aware(
        datetime.combine(inicio, time.min)
    )

    fim_dt = timezone.make_aware(
        datetime.combine(fim, time.max)
    )

    filtros = _anomalia_relatorio_filtro_base() & Q(
        data_registo__range=(inicio_dt, fim_dt)
    )

    sala_id = request.GET.get("sala")
    if sala_id:
        filtros &= (
            Q(sala_id=sala_id)
            | Q(computador__sala_id=sala_id)
        )

    estado = request.GET.get("estado")
    if estado:
        filtros &= Q(estado=estado)

    prioridade = request.GET.get("prioridade")
    if prioridade:
        filtros &= Q(prioridade=prioridade)

    tipo = request.GET.get("tipo")
    if tipo:
        filtros &= Q(tipo=tipo)

    anomalias = filter_anomalias_for_user(
        Anomalia.objects.filter(filtros)
        .select_related(
            "computador",
            "sala",
            "reportado_por",
        )
        .order_by("-data_registo"),
        request.user,
    )

    total_anomalias = anomalias.count()
    total_resolvidas = anomalias.filter(
        estado="RESOLVIDO"
    ).count()
    total_pendentes = anomalias.filter(
        estado="PENDENTE"
    ).count()
    total_em_resolucao = anomalias.filter(
        estado="EM_RESOLUCAO"
    ).count()

    tempo_medio = _tempo_medio_resolucao(anomalias)

    anomalias = _attach_priority_style(anomalias)

    is_coordenador = request.user.groups.filter(
        name="Coordenador"
    ).exists()

    sala_label = "Todas"
    if sala_id:
        sala_obj = Sala.objects.filter(pk=sala_id).only("numero").first()
        if sala_obj:
            sala_label = f"Sala {sala_obj.numero}"

    estado_label = dict(Anomalia.ESTADO_CHOICES).get(estado, "Todos")
    prioridade_label = dict(Anomalia.PRIORIDADE_CHOICES).get(prioridade, "Todas")
    tipo_label = dict(Anomalia._meta.get_field("tipo").choices).get(tipo, "Todos")

    context = {
        "instituicao_nome": "InstituiÃ§Ã£o de Ensino",
        "data_geracao": timezone.now(),
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "total_anomalias": total_anomalias,
        "total_resolvidas": total_resolvidas,
        "total_pendentes": total_pendentes,
        "total_em_resolucao": total_em_resolucao,
        "tempo_medio_resolucao": tempo_medio,
        "anomalias": anomalias,
        "mostrar_reportado_por": not is_coordenador,
        "mostrar_observacoes": False,
        "filtro_periodo": f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}",
        "filtro_sala": sala_label,
        "filtro_estado": estado_label,
        "filtro_prioridade": prioridade_label,
        "filtro_tipo": tipo_label,
    }

    template = get_template(
        "relatorios/relatorio_pdf.html"
    )

    html = template.render(context)

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = "inline; filename=relatorio_anomalias.pdf"

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
    )

    if pisa_status.err:
        messages.error(
            request,
            "NÃ£o foi possÃ­vel gerar o PDF."
        )
        return redirect("relatorios:form")

    log_action(
        request=request,
        action="GERAR_RELATORIO",
        entity="Relatório de Anomalias",
        description=(
            "Relatório gerado com filtros: "
            f"período={inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}, "
            f"sala={sala_label}, estado={estado_label}, "
            f"prioridade={prioridade_label}, tipo={tipo_label}."
        ),
    )
    return response

@login_required
def relatorio_semanal_pdf(request):
    if not _user_can_access(request.user):
        messages.error(request, "Acesso restrito a Administrador, Coordenador ou TÃ©cnico.")
        return redirect("anomalias:lista_anomalias")

    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)

    anomalias = filter_anomalias_for_user(
        Anomalia.objects.filter(
            _anomalia_relatorio_filtro_base(),
            data_registo__date__range=(inicio, fim),
        )
        .select_related("computador", "sala", "reportado_por", "computador__sala")
        .order_by("-data_registo"),
        request.user,
    )

    total_anomalias = anomalias.count()
    total_resolvidas = anomalias.filter(estado="RESOLVIDO").count()
    total_pendentes = anomalias.filter(estado="PENDENTE").count()
    total_em_resolucao = anomalias.filter(estado="EM_RESOLUCAO").count()
    tempo_medio = _tempo_medio_resolucao(anomalias)
    anomalias_pendentes = _attach_priority_style(
        anomalias.filter(estado__in=["PENDENTE", "EM_RESOLUCAO"])
    )
    anomalias = _attach_priority_style(anomalias)

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
        "instituicao_nome": "InstituiÃ§Ã£o de Ensino",
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
        "anomalias_pendentes": anomalias_pendentes,
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
    if pisa_status.err:  # type: ignore
        messages.error(request, "NÃ£o foi possÃ­vel gerar o PDF semanal.")
        return redirect("relatorios:form")

    log_action(
        request=request,
        action="GERAR_RELATORIO",
        entity="Relatório Semanal",
        description=(
            f"Relatório semanal gerado para o período "
            f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}."
        ),
    )
    return response

