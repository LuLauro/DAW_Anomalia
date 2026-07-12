from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from anomalias.models import Anomalia
from auditoria.services import log_action
from users.permissions import group_required, is_admin, is_tecnico


def _has_tecnico_access(user):
    return user.is_authenticated and (
        user.is_staff or is_admin(user) or is_tecnico(user)
    )


def _require_tecnico(request):
    return _has_tecnico_access(request.user)


def _prioridade_counts(queryset):
    return {
        "total_criticas": queryset.filter(prioridade="CRITICA").count(),
        "total_altas": queryset.filter(prioridade="ALTA").count(),
        "total_medias": queryset.filter(prioridade="MEDIA").count(),
        "total_baixas": queryset.filter(prioridade="BAIXA").count(),
    }


@login_required
@group_required(
    _has_tecnico_access,
    error_message="Acesso restrito ao grupo Técnico.",
    redirect_to="anomalias:lista_anomalias",
)
def dashboard(request):
    anomalias_abertas = (
        Anomalia.objects.filter(ativo=True, estado__in=["PENDENTE", "EM_RESOLUCAO"])
        .select_related("computador", "sala", "computador__sala")
        .order_by("-data_registo")
    )
    total_resolvidas = Anomalia.objects.filter(estado="RESOLVIDO").count()
    prioridade_counts = _prioridade_counts(Anomalia.objects.filter(ativo=True))

    context = {
        "total_pendentes": anomalias_abertas.filter(estado="PENDENTE").count(),
        "total_em_resolucao": anomalias_abertas.filter(estado="EM_RESOLUCAO").count(),
        "total_resolvidas": total_resolvidas,
        "anomalias_recentes": anomalias_abertas[:10],
        **prioridade_counts,
    }
    return render(request, "tecnico/dashboard.html", context)


@login_required
def lista_anomalias(request):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalias = (
        Anomalia.objects.filter(ativo=True, estado__in=["PENDENTE", "EM_RESOLUCAO"])
        .select_related("computador", "sala", "computador__sala")
        .annotate(
            sala_ordenacao=Coalesce("sala__numero", "computador__sala__numero")
        )
        .order_by("-data_registo", "sala_ordenacao")
    )
    return render(request, "tecnico/lista_anomalias.html", {"anomalias": anomalias})


@login_required
def historico_anomalias(request):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalias = (
        Anomalia.objects.filter(data_resolvida__isnull=False)
        .select_related("computador", "sala", "computador__sala")
        .order_by("-data_resolvida", "-data_registo")
    )
    return render(request, "tecnico/historico_anomalias.html", {"anomalias": anomalias})


@login_required
def detalhe_anomalia(request, pk):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalia = get_object_or_404(
        Anomalia.objects.select_related(
            "computador", "sala", "computador__sala", "reportado_por"
        ),
        pk=pk,
    )
    anexos = anomalia.anexos.all().order_by("-data_upload")  # type: ignore
    return render(
        request,
        "tecnico/detalhe_anomalia.html",
        {"anomalia": anomalia, "anexos": anexos},
    )


@login_required
def atualizar_estado(request, pk):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalia = get_object_or_404(
        Anomalia.objects.select_related("computador", "sala", "computador__sala"),
        pk=pk,
    )

    if anomalia.estado == "RESOLVIDO":
        messages.warning(request, "Não é possível alterar anomalias resolvidas.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    if request.method != "POST":
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    transicoes = {
        "PENDENTE": "EM_RESOLUCAO",
        "EM_RESOLUCAO": "RESOLVIDO",
    }
    proximo_estado = transicoes.get(anomalia.estado)
    estado_pedido = request.POST.get("estado")

    if not proximo_estado or estado_pedido != proximo_estado:
        messages.error(request, "Transição de estado inválida.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    estado_anterior = anomalia.get_estado_display()
    if estado_pedido == "RESOLVIDO":
        anomalia.marcar_resolvido()
    else:
        anomalia.estado = estado_pedido
        anomalia.save()

    log_action(
        request=request,
        action="ALTERAR_ESTADO_ANOMALIA",
        entity=anomalia,
        description=(
            f"Estado da anomalia '{anomalia.titulo}' alterado de "
            f"{estado_anterior} para {anomalia.get_estado_display()} pelo técnico."
        ),
    )
    messages.success(request, "Estado atualizado com sucesso.")
    return redirect("tecnico:detalhe_anomalia", pk=pk)


@login_required
def adicionar_observacao(request, pk):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalia = get_object_or_404(
        Anomalia.objects.select_related("computador", "sala", "computador__sala"),
        pk=pk,
    )

    if anomalia.estado == "RESOLVIDO":
        messages.warning(request, "Não é possível alterar anomalias resolvidas.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    if request.method != "POST":
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    observacao = (request.POST.get("observacao") or "").strip()
    if not observacao:
        messages.error(request, "A observação não pode estar vazia.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    anomalia.adicionar_observacao(observacao)
    log_action(
        request=request,
        action="ADICIONAR_OBSERVACAO_ANOMALIA",
        entity=anomalia,
        description=f"Observação adicionada à anomalia '{anomalia.titulo}'.",
    )
    messages.success(request, "Observação adicionada com sucesso.")
    return redirect("tecnico:detalhe_anomalia", pk=pk)
