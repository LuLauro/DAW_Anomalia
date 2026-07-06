from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Computador
from .forms import ComputadorForm, FiltroComputadorForm
from users.access import filter_computadores_for_user
from users.permissions import can_access_computadores, group_required

_COMPUTADORES_ACCESS_DENIED = "Não tem permissão para aceder ao módulo Computadores."


@login_required
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def lista_computadores(request):
    form = FiltroComputadorForm(request.GET or None, user=request.user)
    computadores = filter_computadores_for_user(
        Computador.objects.all(), request.user
    ).order_by('sala__numero', 'numero_identificacao')

    if form.is_valid():
        sala = form.cleaned_data.get('sala')
        if sala:
            computadores = computadores.filter(sala=sala)

    return render(request, 'computadores/lista_computadores.html', {
        'computadores': computadores,
        'form': form
    })


@login_required
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def registar_computador(request):
    if request.method == 'POST':
        form = ComputadorForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Computador registado com sucesso!')
            return redirect('computadores:lista_computadores')
    else:
        sala_id = request.GET.get('sala')
        initial_data = {}
        if sala_id:
            initial_data['sala'] = sala_id
        form = ComputadorForm(initial=initial_data, user=request.user)
    return render(request, 'computadores/registar_computador.html', {'form': form})


@login_required
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def detalhe_computador(request, pk):
    computador = get_object_or_404(
        filter_computadores_for_user(Computador.objects.all(), request.user),
        pk=pk,
    )
    # uso getattr para evitar warning do Pylance
    anomalias = getattr(computador, 'anomalias', Computador.objects.none()).all()
    return render(request, 'computadores/detalhe_computador.html', {
        'computador': computador,
        'anomalias': anomalias
    })
