from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Anomalia
from .forms import AnomaliaForm, AnomaliaFilterForm, ObservacaoForm, FiltroHistoricoForm, RelatorioAnomaliasForm, AnomaliaGeralForm
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.utils.timezone import now  

@login_required
def lista_anomalias(request):
    anomalias = Anomalia.objects.filter(ativo=True).order_by('-data_registo')
    form = AnomaliaFilterForm(request.GET)

    if form.is_valid():
        if form.cleaned_data.get('sala'):
            anomalias = anomalias.filter(
                computador__sala=form.cleaned_data['sala'])
        if form.cleaned_data.get('estado'):
            anomalias = anomalias.filter(estado=form.cleaned_data['estado'])

    context = {
        'anomalias': anomalias,
        'form': form,
    }
    return render(request, 'anomalias/lista_anomalias.html', context)

@login_required
def registar_anomalia(request):
    if request.method == 'POST':
        form = AnomaliaForm(request.POST)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.save()

            # Criar mensagem
            mensagem = f"""
Foi registada uma nova anomalia no sistema.

Título: {anomalia.titulo}
Computador: {anomalia.computador or "Sem computador"}
Sala: {anomalia.computador.sala if anomalia.computador else "N/A"}
Descrição: {anomalia.descricao}

Reportado por: {request.user.get_full_name()} ({request.user.email})
"""

            # Obter emails de admins e coordenadores
            grupos = Group.objects.filter(name__in=['Administrador', 'Coordenador'])
            destinatarios = set()

            for grupo in grupos:
                for user in grupo.user_set.all():
                    if user.email:
                        destinatarios.add(user.email)

            if destinatarios:
                send_mail(
                    subject='Nova Anomalia Criada',
                    message=mensagem,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=list(destinatarios),
                    fail_silently=False,
                )

            messages.success(request, 'Anomalia registada com sucesso!')
            return redirect('anomalias:lista_anomalias')
    else:
        computador_id = request.GET.get('computador')
        initial_data = {}
        if computador_id:
            initial_data['computador'] = computador_id
        form = AnomaliaForm(initial=initial_data)
    return render(request, 'anomalias/registar_anomalia.html', {'form': form})


@login_required
def atualizar_estado(request, pk):
    anomalia = get_object_or_404(Anomalia, pk=pk)

    # Bloquear coordenadores
    if request.user.groups.filter(name='Coordenador').exists():
        messages.warning(request, "Coordenadores não têm permissão para alterar o estado.")
        return redirect('anomalias:lista_anomalias')
    
    # Professores só podem alterar suas próprias anomalias
    if request.user.groups.filter(name='Professor').exists():
        if anomalia.reportado_por != request.user:
            messages.warning(request, "Você só pode alterar o estado das anomalias que você registou.")
            return redirect('anomalias:lista_anomalias')
        
    if request.method == 'POST':
        novo_estado = request.POST.get('estado')
        if novo_estado in dict(Anomalia.ESTADO_CHOICES):
            anomalia.estado = novo_estado
            if novo_estado == 'RESOLVIDO':
                anomalia.data_resolvida = now()
            anomalia.save()
            messages.success(request, 'Estado atualizado com sucesso!')

            mensagem = f"""
O estado de uma anomalia foi atualizado.

Título: {anomalia.titulo}
Novo estado: {anomalia.estado}
Computador: {anomalia.computador or "Sem computador"}
Sala: {anomalia.computador.sala if anomalia.computador else "N/A"}

Alterado por: {request.user.get_full_name()} ({request.user.email})
"""

            # Obter emails dos grupos relevantes
            grupos = Group.objects.filter(name__in=['Administrador', 'Coordenador'])
            destinatarios = set()

            for grupo in grupos:
                for user in grupo.user_set.all():
                    if user.email:
                        destinatarios.add(user.email)

            if destinatarios:
                send_mail(
                    subject='Anomalia Atualizada',
                    message=mensagem,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=list(destinatarios),
                    fail_silently=False,
                )

    return redirect('anomalias:lista_anomalias')


@login_required
def adicionar_observacao(request, pk):
    anomalia = get_object_or_404(Anomalia, pk=pk)

    if request.user.groups.filter(name='Professor').exists():
        messages.warning(request, "Você não tem permissão para adicionar observações.")
        return redirect('anomalias:lista_anomalias')

    if request.method == 'POST':
        form = ObservacaoForm(request.POST, instance=anomalia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Observação adicionada com sucesso.')
            return redirect('anomalias:lista_anomalias')
    else:
        form = ObservacaoForm(instance=anomalia)

    return render(request, 'anomalias/adicionar_observacao.html', {'form': form, 'anomalia': anomalia})
    

@login_required
def historico_anomalias(request):
    form = FiltroHistoricoForm(request.GET or None)
    anomalias = Anomalia.objects.filter(data_resolvida__isnull=False).select_related('computador', 'computador__sala')

    if form.is_valid():

        data_resolucao = form.cleaned_data.get('data_resolucao')
        sala = form.cleaned_data.get('sala')
        computador = form.cleaned_data.get('computador')
        
        if data_resolucao:
            anomalias = anomalias.filter(data_resolvida__date__lte=data_resolucao)
        if sala:
            anomalias = anomalias.filter(computador__sala=sala)
        if computador:
            anomalias = anomalias.filter(computador=computador)

    return render(request, 'anomalias/historico_anomalias.html', {
        'anomalias': anomalias.order_by('-data_resolvida'),
        'form': form
    })


@login_required
def eliminar_anomalia(request, pk):
    anomalia = get_object_or_404(Anomalia, pk=pk)

    if not request.user.is_superuser:
        messages.warning(request, "Apenas administradores podem eliminar anomalias.")
        return redirect('anomalias:lista_anomalias')

    if anomalia.estado != 'RESOLVIDO':
        messages.warning(request, "Só é possível eliminar anomalias que foram resolvidas.")
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
        form = AnomaliaGeralForm(request.POST)
        if form.is_valid():
            anomalia = form.save(commit=False)
            anomalia.reportado_por = request.user
            anomalia.save()

            # Criar mensagem
            mensagem = f"""
Foi registada uma nova anomalia geral no sistema.

Título: {anomalia.titulo}
Descrição: {anomalia.descricao}

Reportado por: {request.user.get_full_name()} ({request.user.email})
"""

            # Obter emails de administradores e coordenadores
            grupos = Group.objects.filter(name__in=['Administrador', 'Coordenador'])
            destinatarios = set()

            for grupo in grupos:
                for user in grupo.user_set.all():
                    if user.email:
                        destinatarios.add(user.email)

            # Enviar email
            if destinatarios:
                send_mail(
                    subject='Nova Anomalia Geral Criada',
                    message=mensagem,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=list(destinatarios),
                    fail_silently=False,
                )

            messages.success(request, 'Anomalia geral registada com sucesso.')
            return redirect('anomalias:lista_anomalias')
    else:
        form = AnomaliaGeralForm()
    
    return render(request, 'anomalias/registar_anomalia_geral.html', {'form': form})


def teste_email(request):
    send_mail(
        subject='Teste de E-mail',
        message='Este é um e-mail de teste enviado pelo Django.',
        from_email='laurolulauro@gmail.com',
        recipient_list=['luisasgl22@gmail.com'],  
        fail_silently=False,
    )
    return HttpResponse("Email enviado com sucesso!")