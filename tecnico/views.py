from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.functions import Coalesce

from anomalias.models import Anomalia
from users.utils import is_tecnico


def _require_tecnico(request):
    if not is_tecnico(request.user):
        messages.error(request, "Acesso restrito ao grupo Tecnico.")
        return False
    return True


@login_required
def dashboard(request):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalias_abertas = (
        Anomalia.objects.filter(ativo=True, estado__in=["PENDENTE", "EM_RESOLUCAO"])
        .select_related("computador", "sala")
        .order_by("-data_registo")
    )
    total_resolvidas = Anomalia.objects.filter(ativo=True, estado="RESOLVIDO").count()

    context = {
        "total_pendentes": anomalias_abertas.filter(estado="PENDENTE").count(),
        "total_em_resolucao": anomalias_abertas.filter(estado="EM_RESOLUCAO").count(),
        "total_resolvidas": total_resolvidas,
        "anomalias_recentes": anomalias_abertas[:10],
    }
    return render(request, "tecnico/dashboard.html", context)


@login_required
def lista_anomalias(request):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalias = (
        Anomalia.objects.filter(ativo=True, estado__in=["PENDENTE", "EM_RESOLUCAO"])
        .select_related("computador", "sala")
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
        Anomalia.objects.filter(ativo=True, estado="RESOLVIDO")
        .select_related("computador", "sala")
        .order_by("-data_resolvida", "-data_registo")
    )
    return render(request, "tecnico/historico_anomalias.html", {"anomalias": anomalias})


@login_required
def detalhe_anomalia(request, pk):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalia = get_object_or_404(
        Anomalia.objects.select_related("computador", "sala"), pk=pk
    )
    anexos = anomalia.anexos.all().order_by("-data_upload") # type: ignore
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
        Anomalia.objects.select_related("computador", "sala"), pk=pk
    )

    if anomalia.estado == "RESOLVIDO":
        messages.warning(request, "Nao e possivel alterar anomalias resolvidas.")
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
        messages.error(request, "Transicao de estado invalida.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    if estado_pedido == "RESOLVIDO":
        anomalia.marcar_resolvido()
    else:
        anomalia.estado = estado_pedido
        anomalia.save()

    messages.success(request, "Estado atualizado com sucesso.")
    return redirect("tecnico:detalhe_anomalia", pk=pk)


@login_required
def adicionar_observacao(request, pk):
    if not _require_tecnico(request):
        return redirect("anomalias:lista_anomalias")

    anomalia = get_object_or_404(
        Anomalia.objects.select_related("computador", "sala"), pk=pk
    )

    if anomalia.estado == "RESOLVIDO":
        messages.warning(request, "Nao e possivel alterar anomalias resolvidas.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    if request.method != "POST":
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    observacao = (request.POST.get("observacao") or "").strip()
    if not observacao:
        messages.error(request, "A observacao nao pode estar vazia.")
        return redirect("tecnico:detalhe_anomalia", pk=pk)

    anomalia.adicionar_observacao(observacao)
    messages.success(request, "Observacao adicionada com sucesso.")
    return redirect("tecnico:detalhe_anomalia", pk=pk)
