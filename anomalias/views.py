from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from computadores.models import Computador
from salas.models import Sala
from users.access import (
    filter_anomalias_for_user,
    filter_computadores_for_user,
    filter_salas_for_user,
)
from users.permissions import (
    can_add_observacao,
    can_delete_anomalia,
    can_view_anomalia,
    is_admin,
)

from .forms import (
    AnomaliaFilterForm,
    AnomaliaForm,
    AnomaliaGeralForm,
    AnomaliaPrioridadeForm,
    FiltroHistoricoForm,
)
from .models import AnexoAnomalia, Anomalia
from .utils import (
    enviar_email_destinatarios,
    get_email_recipients_for_new_anomaly,
    get_email_recipients_for_status_change,
)


def _get_registar_anomalia_initial(request):
    initial = {}
    salas = filter_salas_for_user(Sala.objects.all(), request.user)
    computadores = filter_computadores_for_user(
        Computador.objects.select_related("sala"),
        request.user,
    )

    sala_param = request.GET.get("sala")
    pc_param = request.GET.get("pc")

    sala = None
    computador = None

    if sala_param:
        try:
            sala = salas.get(pk=sala_param)
        except (Sala.DoesNotExist, TypeError, ValueError):
            sala = None

    if pc_param:
        try:
            computador = computadores.get(pk=pc_param)
        except (Computador.DoesNotExist, TypeError, ValueError):
            computador = None

    if sala and computador and computador.sala_id != sala.pk:
        computador = None

    if sala:
        initial["sala"] = sala.pk

    if computador:
        initial["computador"] = computador.pk
        initial.setdefault("sala", computador.sala_id)

    return initial


@login_required
def lista_anomalias(request):
    anomalias = filter_anomalias_for_user(
        Anomalia.objects.filter(ativo=True)
        .select_related("computador", "sala", "computador__sala", "reportado_por")
        .annotate(
            prioridade_ordem=Case(
                When(prioridade="CRITICA", then=Value(0)),
                When(prioridade="ALTA", then=Value(1)),
                When(prioridade="MEDIA", then=Value(2)),
                When(prioridade="BAIXA", then=Value(3)),
                default=Value(99),
                output_field=IntegerField(),
            )
        ),
        request.user,
    )

    form = AnomaliaFilterForm(request.GET, user=request.user)
    if form.is_valid():
        pesquisa = (form.cleaned_data.get("pesquisa") or "").strip()
        sala = form.cleaned_data.get("sala")
        estado = form.cleaned_data.get("estado")
        prioridade = form.cleaned_data.get("prioridade")
        ordenacao = form.cleaned_data.get("ordenacao") or "recentes"
        if pesquisa:
            prioridade_map = {
                "critica": "CRITICA",
                "crítica": "CRITICA",
                "alta": "ALTA",
                "media": "MEDIA",
                "média": "MEDIA",
                "baixa": "BAIXA",
            }
            prioridade_pesquisa = prioridade_map.get(pesquisa.lower())
            pesquisa_q = Q(titulo__icontains=pesquisa) | Q(descricao__icontains=pesquisa)
            if prioridade_pesquisa:
                pesquisa_q |= Q(prioridade=prioridade_pesquisa)
            anomalias = anomalias.filter(pesquisa_q)
        if sala:
            anomalias = anomalias.filter(sala=sala) | anomalias.filter(
                computador__sala=sala
            )
        if estado:
            anomalias = anomalias.filter(estado=estado)
        if prioridade:
            anomalias = anomalias.filter(prioridade=prioridade)
        if ordenacao == "prioridade":
            anomalias = anomalias.order_by("prioridade_ordem", "-data_registo")
        else:
            anomalias = anomalias.order_by("-data_registo")
    else:
        anomalias = anomalias.order_by("-data_registo")

    paginator = Paginator(anomalias, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "anomalias": page_obj.object_list,
        "page_obj": page_obj,
        "form": form,
        "can_delete_resolved": is_admin(request.user),
    }
    return render(request, "anomalias/lista_anomalias.html", context)


@login_required
def registar_anomalia(request):
    if request.method == "POST":
        form = AnomaliaForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.full_clean()
            anomalia.save()
            _criar_anexos(
                anomalia,
                form.cleaned_data.get("imagens"),
                form.cleaned_data.get("videos"),
            )

            mensagem = f"""
Foi registada uma nova anomalia.

Título: {anomalia.titulo}
Computador: {anomalia.computador or "Sem computador"}
Sala: {anomalia.computador.sala if anomalia.computador else "N/A"}
Descrição: {anomalia.descricao}
Reportado por: {request.user.get_full_name()} ({request.user.email})
"""
            enviar_email_destinatarios(
                "Nova Anomalia Criada",
                mensagem,
                get_email_recipients_for_new_anomaly(anomalia, request.user),
            )
            messages.success(request, "Anomalia registada com sucesso!")
            return redirect("anomalias:lista_anomalias")
    else:
        form = AnomaliaForm(
            user=request.user,
            initial=_get_registar_anomalia_initial(request),
        )
    return render(request, "anomalias/registar_anomalia.html", {"form": form})


@login_required
def atualizar_estado(request, pk):
    anomalia = get_object_or_404(
        filter_anomalias_for_user(
            Anomalia.objects.select_related("computador", "sala"),
            request.user,
        ),
        pk=pk,
    )

    if request.user.groups.filter(name="Coordenador").exists():
        messages.warning(request, "Coordenadores não podem alterar o estado.")
        return redirect("anomalias:lista_anomalias")

    if (
        request.user.groups.filter(name="Professor").exists()
        and anomalia.reportado_por != request.user
    ):
        messages.warning(
            request, "Professores só podem alterar o estado das suas próprias anomalias."
        )
        return redirect("anomalias:lista_anomalias")

    if request.method == "POST":
        novo_estado = request.POST.get("estado")
        if novo_estado in dict(Anomalia.ESTADO_CHOICES):
            anomalia.estado = novo_estado
            if novo_estado == "RESOLVIDO":
                anomalia.marcar_resolvido()
            else:
                anomalia.save()

            mensagem = f"""
O estado de uma anomalia foi atualizado.

Título: {anomalia.titulo}
Novo estado: {anomalia.estado}
Computador: {anomalia.computador or "Sem computador"}
Sala: {anomalia.computador.sala if anomalia.computador else "N/A"}
Alterado por: {request.user.get_full_name()} ({request.user.email})
"""
            enviar_email_destinatarios(
                "Anomalia Atualizada",
                mensagem,
                get_email_recipients_for_status_change(anomalia, request.user),
            )
            messages.success(request, "Estado atualizado com sucesso!")
    return redirect("anomalias:lista_anomalias")


@login_required
def atualizar_prioridade(request, pk):
    anomalia = get_object_or_404(
        filter_anomalias_for_user(
            Anomalia.objects.select_related("computador", "sala"),
            request.user,
        ),
        pk=pk,
    )

    if anomalia.estado == "RESOLVIDO":
        messages.warning(
            request, "A prioridade não pode ser alterada depois da resolução."
        )
        return redirect("anomalias:detalhe_anomalia", pk=pk)

    if request.method != "POST":
        return redirect("anomalias:detalhe_anomalia", pk=pk)

    form = AnomaliaPrioridadeForm(request.POST, instance=anomalia)
    if form.is_valid():
        anomalia = form.save(commit=False)
        anomalia.full_clean()
        anomalia.save(update_fields=["prioridade"])
        messages.success(request, "Prioridade atualizada com sucesso.")
    else:
        messages.error(request, "Não foi possível atualizar a prioridade.")

    return redirect("anomalias:detalhe_anomalia", pk=pk)


@login_required
def adicionar_observacao(request, pk):
    anomalia = get_object_or_404(
        filter_anomalias_for_user(Anomalia.objects.all(), request.user),
        pk=pk,
    )

    if not can_add_observacao(request.user, anomalia):
        messages.warning(
            request, "Você não tem permissão para adicionar observações."
        )
        return redirect("anomalias:lista_anomalias")

    return redirect("anomalias:detalhe_anomalia", pk=anomalia.pk)


def _criar_anexos(anomalia, imagens, videos):
    imagens = imagens or []
    videos = videos or []
    anexos = []
    for imagem in imagens:
        anexos.append(AnexoAnomalia(anomalia=anomalia, arquivo=imagem, tipo="IMAGEM"))
    for video in videos:
        anexos.append(AnexoAnomalia(anomalia=anomalia, arquivo=video, tipo="VIDEO"))
    if anexos:
        AnexoAnomalia.objects.bulk_create(anexos)


@login_required
def detalhe_anomalia(request, pk):
    anomalia = get_object_or_404(
        filter_anomalias_for_user(
            Anomalia.objects.select_related(
                "computador", "sala", "computador__sala", "reportado_por"
            ),
            request.user,
        ),
        pk=pk,
    )

    anexos = anomalia.anexos.all().order_by("-data_upload")
    prioridade_form = None
    if anomalia.estado != "RESOLVIDO":
        prioridade_form = AnomaliaPrioridadeForm(instance=anomalia)

    return render(
        request,
        "anomalias/detalhe_anomalia.html",
        {
            "anomalia": anomalia,
            "anexos": anexos,
            "prioridade_form": prioridade_form,
        },
    )


@login_required
def ver_anexo(request, pk):
    anexo = get_object_or_404(
        AnexoAnomalia.objects.select_related(
            "anomalia", "anomalia__sala", "anomalia__computador__sala"
        ),
        pk=pk,
    )
    if not can_view_anomalia(request.user, anexo.anomalia):
        raise Http404()
    return FileResponse(anexo.arquivo.open("rb"), as_attachment=False)


@login_required
def historico_anomalias(request):
    form = FiltroHistoricoForm(request.GET or None, user=request.user)
    anomalias = filter_anomalias_for_user(
        Anomalia.objects.filter(data_resolvida__isnull=False).select_related(
            "computador", "sala", "computador__sala"
        ),
        request.user,
    )
    if form.is_valid():
        if form.cleaned_data.get("data_resolvida"):
            anomalias = anomalias.filter(
                data_resolvida__date__lte=form.cleaned_data["data_resolvida"]
            )
        if form.cleaned_data.get("sala"):
            sala = form.cleaned_data["sala"]
            anomalias = anomalias.filter(sala=sala) | anomalias.filter(
                computador__sala=sala
            )
        if form.cleaned_data.get("computador"):
            anomalias = anomalias.filter(computador=form.cleaned_data["computador"])
    return render(
        request,
        "anomalias/historico_anomalias.html",
        {"anomalias": anomalias.order_by("-data_resolvida"), "form": form},
    )


@login_required
def eliminar_anomalia(request, pk):
    anomalia = get_object_or_404(
        filter_anomalias_for_user(Anomalia.objects.all(), request.user),
        pk=pk,
    )
    if not can_delete_anomalia(request.user, anomalia):
        messages.warning(
            request, "Apenas administradores podem eliminar anomalias resolvidas."
        )
        return redirect("anomalias:lista_anomalias")

    if request.method == "POST":
        anomalia.ativo = False
        anomalia.save(update_fields=["ativo"])
        messages.success(request, "Anomalia removida da lista principal com sucesso.")
        return redirect("anomalias:lista_anomalias")

    return render(request, "anomalias/confirmar_eliminar.html", {"anomalia": anomalia})


@login_required
def registar_anomalia_geral(request):
    if request.method == "POST":
        form = AnomaliaGeralForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.full_clean()
            anomalia.save()
            _criar_anexos(
                anomalia,
                form.cleaned_data.get("imagens"),
                form.cleaned_data.get("videos"),
            )

            mensagem = f"""
Foi registada uma nova anomalia geral.

Título: {anomalia.titulo}
Descrição: {anomalia.descricao}
Sala: {anomalia.sala.numero if anomalia.sala else "N/A"}
Reportado por: {request.user.get_full_name()} ({request.user.email})
"""
            enviar_email_destinatarios(
                "Nova Anomalia Geral Criada",
                mensagem,
                get_email_recipients_for_new_anomaly(anomalia, request.user),
            )
            messages.success(request, "Anomalia geral registada com sucesso.")
            return redirect("anomalias:lista_anomalias")
    else:
        form = AnomaliaGeralForm(user=request.user)
    return render(request, "anomalias/registar_anomalia_geral.html", {"form": form})


@login_required
def computadores_por_sala(request):
    sala_id = request.GET.get("sala_id")
    if not sala_id:
        return JsonResponse({"computadores": []})

    computadores = (
        filter_computadores_for_user(Computador.objects.all(), request.user)
        .filter(sala_id=sala_id)
        .order_by("numero_identificacao")
        .values("id", "numero_identificacao")
    )
    data = [
        {
            "id": computador["id"],
            "text": f"PC {computador['numero_identificacao']}",
        }
        for computador in computadores
    ]
    return JsonResponse({"computadores": data})
