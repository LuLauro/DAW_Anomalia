from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Anomalia, AnexoAnomalia
from .forms import AnomaliaForm, AnomaliaGeralForm, AnomaliaFilterForm, ObservacaoForm, FiltroHistoricoForm
from django.utils.timezone import now
from .utils import enviar_email_grupos
from django.contrib.auth.models import Group
from users.permissions import (
    can_add_observacao,
    can_change_estado,
    can_delete_anomalia,
    can_view_anomalia,
)

@login_required
def lista_anomalias(request):
    anomalias = Anomalia.objects.filter(ativo=True).select_related('computador', 'sala').order_by('-data_registo')
    if request.user.groups.filter(name='Professor').exists():
        anomalias = anomalias.filter(reportado_por=request.user)
    form = AnomaliaFilterForm(request.GET)
    if form.is_valid():
        sala = form.cleaned_data.get('sala')
        estado = form.cleaned_data.get('estado')
        if sala:
            anomalias = anomalias.filter(sala=sala)
        if estado:
            anomalias = anomalias.filter(estado=estado)
    return render(request, 'anomalias/lista_anomalias.html', {'anomalias': anomalias, 'form': form})

@login_required
def registar_anomalia(request):
    if request.method == 'POST':
        form = AnomaliaForm(request.POST, request.FILES)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.save()
            _criar_anexos(anomalia, form.cleaned_data.get("imagens"), form.cleaned_data.get("videos"))

            mensagem = f"""
Foi registada uma nova anomalia.

Título: {anomalia.titulo}
Computador: {anomalia.computador or "Sem computador"}
Sala: {anomalia.computador.sala if anomalia.computador else "N/A"}
Descrição: {anomalia.descricao}
Reportado por: {request.user.get_full_name()} ({request.user.email})
"""
            enviar_email_grupos('Nova Anomalia Criada', mensagem)
            messages.success(request, 'Anomalia registada com sucesso!')
            return redirect('anomalias:lista_anomalias')
    else:
        form = AnomaliaForm()
    return render(request, 'anomalias/registar_anomalia.html', {'form': form})

@login_required
def atualizar_estado(request, pk):
    anomalia = get_object_or_404(Anomalia.objects.select_related('computador', 'sala'), pk=pk)

    if request.user.groups.filter(name='Coordenador').exists():
        messages.warning(request, "Coordenadores não podem alterar o estado.")
        return redirect('anomalias:lista_anomalias')

    if request.user.groups.filter(name='Professor').exists() and anomalia.reportado_por != request.user:
        messages.warning(request, "Professores só podem alterar suas próprias anomalias.")
        return redirect('anomalias:lista_anomalias')

    if request.method == 'POST':
        novo_estado = request.POST.get('estado')
        if novo_estado in dict(Anomalia.ESTADO_CHOICES):
            anomalia.estado = novo_estado
            if novo_estado == 'RESOLVIDO':
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
            enviar_email_grupos('Anomalia Atualizada', mensagem)
            messages.success(request, 'Estado atualizado com sucesso!')
    return redirect('anomalias:lista_anomalias')

@login_required
def adicionar_observacao(request, pk):
    anomalia = get_object_or_404(Anomalia, pk=pk)

    if not can_add_observacao(request.user, anomalia):
        messages.warning(request, "Você não tem permissão para adicionar observações.")
        return redirect("anomalias:lista_anomalias")

    if request.method == "POST":
        texto = request.POST.get("texto", "").strip()

        if texto:
            Observacao.objects.create(
                anomalia=anomalia,
                autor=request.user,
                texto=texto,
            )
            messages.success(request, "Observação adicionada com sucesso.")

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
    anomalia = get_object_or_404(Anomalia, pk=pk)

    if not can_view_anomalia(request.user, anomalia):
        messages.warning(request, "Você não tem permissão para ver esta anomalia.")
        return redirect("anomalias:lista_anomalias")

    anexos = anomalia.anexos.all().order_by("-data_upload")

    return render(
        request,
        "tecnico/detalhe_anomalia.html",
        {"anomalia": anomalia, "anexos": anexos},
    )
    
@login_required
def ver_anexo(request, pk):
    anexo = get_object_or_404(AnexoAnomalia, pk=pk)
    if request.user.groups.filter(name='Professor').exists() and anexo.anomalia.reportado_por != request.user:
        raise Http404()
    return FileResponse(anexo.arquivo.open("rb"), as_attachment=False)

@login_required
def historico_anomalias(request):
    form = FiltroHistoricoForm(request.GET or None)
    anomalias = Anomalia.objects.filter(data_resolvida__isnull=False).select_related('computador', 'sala')
    if form.is_valid():
        if form.cleaned_data.get('data_resolvida'):
            anomalias = anomalias.filter(data_resolvida__date__lte=form.cleaned_data['data_resolvida'])
        if form.cleaned_data.get('sala'):
            anomalias = anomalias.filter(sala=form.cleaned_data['sala'])
        if form.cleaned_data.get('computador'):
            anomalias = anomalias.filter(computador=form.cleaned_data['computador'])
    return render(request, 'anomalias/historico_anomalias.html', {'anomalias': anomalias.order_by('-data_resolvida'), 'form': form})

@login_required
def eliminar_anomalia(request, pk):
    anomalia = get_object_or_404(Anomalia, pk=pk)
    if not request.user.is_superuser:
        messages.warning(request, "Apenas administradores podem eliminar anomalias.")
        return redirect('anomalias:lista_anomalias')
    if anomalia.estado != 'RESOLVIDO':
        messages.warning(request, "Só é possível eliminar anomalias resolvidas.")
        return redirect('anomalias:lista_anomalias')

    if request.method == 'POST':
        anomalia.ativo = False
        anomalia.save()
        messages.success(request, "Anomalia eliminada com sucesso.")
        return redirect('anomalias:lista_anomalias')
    return render(request, 'anomalias/confirmar_eliminar.html', {'anomalia': anomalia})

@login_required
def registar_anomalia_geral(request):
    if request.method == 'POST':
        form = AnomaliaGeralForm(request.POST, request.FILES)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.save()
            _criar_anexos(anomalia, form.cleaned_data.get("imagens"), form.cleaned_data.get("videos"))

            mensagem = f"""
Foi registada uma nova anomalia geral.

Título: {anomalia.titulo}
Descrição: {anomalia.descricao}
Reportado por: {request.user.get_full_name()} ({request.user.email})
"""
            enviar_email_grupos('Nova Anomalia Geral Criada', mensagem)
            messages.success(request, 'Anomalia geral registada com sucesso.')
            return redirect('anomalias:lista_anomalias')
    else:
        form = AnomaliaGeralForm()
    return render(request, 'anomalias/registar_anomalia_geral.html', {'form': form})

