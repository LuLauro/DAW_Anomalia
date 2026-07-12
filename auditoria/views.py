from datetime import datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from auditoria.models import LogAuditoria
from users.permissions import is_admin


def _parse_date_range(date_str, end_of_day=False):
    if not date_str:
        return None
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    base_time = time.max if end_of_day else time.min
    return timezone.make_aware(datetime.combine(parsed, base_time))


@login_required
def lista_logs(request):
    if not is_admin(request.user):
        return redirect("dashboard:index")

    audit_table_exists = (
        LogAuditoria._meta.db_table in connection.introspection.table_names()
    )

    if audit_table_exists:
        logs = LogAuditoria.objects.select_related("utilizador").all()
        utilizadores = (
            User.objects.filter(logs_auditoria__isnull=False)
            .distinct()
            .order_by("username")
        )
        acoes = (
            LogAuditoria.objects.order_by("acao")
            .values_list("acao", flat=True)
            .distinct()
        )
    else:
        messages.warning(
            request,
            "A tabela de auditoria ainda não existe. Aplique a migration para ativar os registos.",
        )
        logs = LogAuditoria.objects.none()
        utilizadores = User.objects.none()
        acoes = []

    pesquisa = (request.GET.get("pesquisa") or "").strip()
    utilizador_id = (request.GET.get("utilizador") or "").strip()
    acao = (request.GET.get("acao") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()

    if pesquisa:
        logs = logs.filter(
            Q(descricao__icontains=pesquisa)
            | Q(entidade__icontains=pesquisa)
            | Q(entidade_id__icontains=pesquisa)
            | Q(utilizador__username__icontains=pesquisa)
        )

    if utilizador_id:
        logs = logs.filter(utilizador_id=utilizador_id)

    if acao:
        logs = logs.filter(acao=acao)

    inicio_dt = _parse_date_range(data_inicio)
    if inicio_dt:
        logs = logs.filter(data_hora__gte=inicio_dt)

    fim_dt = _parse_date_range(data_fim, end_of_day=True)
    if fim_dt:
        logs = logs.filter(data_hora__lte=fim_dt)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "auditoria/lista_logs.html",
        {
            "logs": page_obj.object_list,
            "page_obj": page_obj,
            "utilizadores": utilizadores,
            "acoes": acoes,
            "pesquisa": pesquisa,
            "utilizador_id": utilizador_id,
            "acao_selecionada": acao,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )
