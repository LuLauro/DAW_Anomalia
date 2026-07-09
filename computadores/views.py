import base64
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from users.access import filter_computadores_for_user
from users.permissions import can_access_computadores, group_required

from .forms import ComputadorForm, FiltroComputadorForm
from .models import Computador

_COMPUTADORES_ACCESS_DENIED = "Não tem permissão para aceder ao módulo Computadores."


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
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def lista_computadores(request):
    form = FiltroComputadorForm(request.GET or None, user=request.user)
    computadores = filter_computadores_for_user(
        Computador.objects.all(), request.user
    ).order_by("sala__numero", "numero_identificacao")

    if form.is_valid():
        sala = form.cleaned_data.get("sala")
        if sala:
            computadores = computadores.filter(sala=sala)

    paginator = Paginator(computadores, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "computadores/lista_computadores.html",
        {
            "computadores": page_obj.object_list,
            "page_obj": page_obj,
            "form": form,
        },
    )


@login_required
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def registar_computador(request):
    if request.method == "POST":
        form = ComputadorForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Computador registado com sucesso!")
            return redirect("computadores:lista_computadores")
    else:
        sala_id = request.GET.get("sala")
        initial_data = {}
        if sala_id:
            initial_data["sala"] = sala_id
        form = ComputadorForm(initial=initial_data, user=request.user)
    return render(request, "computadores/registar_computador.html", {"form": form})


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
    anomalias = getattr(computador, "anomalias", Computador.objects.none()).all()
    return render(
        request,
        "computadores/detalhe_computador.html",
        {
            "computador": computador,
            "anomalias": anomalias,
        },
    )


@login_required
@group_required(
    can_access_computadores,
    error_message=_COMPUTADORES_ACCESS_DENIED,
    redirect_to="anomalias:lista_anomalias",
)
def qrcode_computador(request, pk):
    computador = get_object_or_404(
        filter_computadores_for_user(
            Computador.objects.select_related("sala"),
            request.user,
        ),
        pk=pk,
    )
    target_url = _build_target_url(
        request,
        f"{reverse('anomalias:registar_anomalia')}?"
        f"{urlencode({'sala': computador.sala_id, 'pc': computador.pk})}",
    )
    return render(
        request,
        "shared/qrcode_detail.html",
        {
            "page_title": f"QR Code do Computador {computador.numero_identificacao}",
            "heading": f"Computador {computador.numero_identificacao}",
            "subtitle": f"Sala {computador.sala.numero}",
            "details": [
                ("Computador", computador.numero_identificacao),
                ("Sala", computador.sala.numero),
                ("Marca", computador.marca or "-"),
                ("Modelo", computador.modelo or "-"),
            ],
            "qr_code_data_uri": _build_qr_code_data_uri(target_url),
            "target_url": target_url,
            "back_url": reverse("computadores:lista_computadores"),
        },
    )
