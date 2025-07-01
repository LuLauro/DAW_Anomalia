from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Sala
from .forms import SalaForm


@login_required
def lista_salas(request):
    salas = Sala.objects.all()
    return render(request, 'salas/lista_salas.html', {'salas': salas})


@login_required
def registar_sala(request):
    if request.method == 'POST':
        form = SalaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala registada com sucesso!')
            return redirect('salas:lista_salas')
    else:
        form = SalaForm()
    return render(request, 'salas/registar_sala.html', {'form': form})


@login_required
def detalhe_sala(request, pk):
    sala = get_object_or_404(Sala, pk=pk)
    computadores = sala.computadores.all()
    return render(request, 'salas/detalhe_sala.html', {
        'sala': sala,
        'computadores': computadores
    })
