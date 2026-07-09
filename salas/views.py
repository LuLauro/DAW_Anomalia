import base64
from io import BytesIO
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import qrcode

from users.access import filter_salas_for_user
from users.permissions import is_coordenador

from .forms import SalaForm
from .models import Sala


def _build_qr_code_data_uri(data):
    image = qrcode.make(data)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _build_target_url(request, path_with_query):
    if settings.QR_CODE_BASE_URL:
        return f"{settings.QR_CODE_BASE_URL.rstrip('/')}{path_with_query}"
    return request.build_absolute_uri(path_with_query)


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


@login_required
def qrcode_sala(request, pk):
    sala = get_object_or_404(
        filter_salas_for_user(Sala.objects.all(), request.user),
        pk=pk,
    )
    target_url = _build_target_url(
        request,
        f"{reverse('anomalias:registar_anomalia')}?{urlencode({'sala': sala.pk})}",
    )
    return render(
        request,
        "shared/qrcode_detail.html",
        {
            "page_title": f"QR Code da Sala {sala.numero}",
            "heading": f"Sala {sala.numero}",
            "subtitle": sala.descricao or "QR Code para registo rápido de anomalias.",
            "details": [
                ("Sala", sala.numero),
                ("Descrição", sala.descricao or "-"),
            ],
            "qr_code_data_uri": _build_qr_code_data_uri(target_url),
            "target_url": target_url,
            "back_url": reverse("salas:lista_salas"),
        },
    )
