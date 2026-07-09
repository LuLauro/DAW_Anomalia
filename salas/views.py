from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from users.access import filter_salas_for_user
from users.permissions import is_coordenador

from .forms import SalaForm
from .models import Sala


@login_required
def lista_salas(request):
    salas = filter_salas_for_user(Sala.objects.all(), request.user)
    paginator = Paginator(salas, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        'salas/lista_salas.html',
        {'salas': page_obj.object_list, 'page_obj': page_obj},
    )


@login_required
def registar_sala(request):
    if is_coordenador(request.user):
        messages.warning(request, "Os coordenadores só podem aceder às salas sob a sua responsabilidade.")
        return redirect('salas:lista_salas')

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
    sala = get_object_or_404(
        filter_salas_for_user(Sala.objects.all(), request.user),
        pk=pk,
    )
    computadores = getattr(sala, 'computadores', Sala.objects.none()).all()
    return render(request, 'salas/detalhe_sala.html', {
        'sala': sala,
        'computadores': computadores
    })
