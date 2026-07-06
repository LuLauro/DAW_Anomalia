from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, F, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from anomalias.models import Anomalia
from computadores.models import Computador
from salas.models import Sala
from users.access import (
    filter_anomalias_for_user,
    filter_computadores_for_user,
    filter_salas_for_user,
)
from users.permissions import is_admin, is_coordenador


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Sessão terminada com sucesso!')
    return redirect('index')


@user_passes_test(is_admin)
def dashboard(request):
    total_salas = Sala.objects.count()
    total_computadores = Computador.objects.count()
    total_anomalias = Anomalia.objects.count()

    anomalias_por_estado = Anomalia.objects.values('estado').annotate(total=Count('id'))

    data_limite = timezone.now() - timedelta(days=7)
    anomalias_recentes = Anomalia.objects.filter(
        data_registo__gte=data_limite
    ).order_by('-data_registo')[:5]

    salas_problematicas = Sala.objects.annotate(
        num_anomalias_computador=Count(
            'computadores__anomalias',
            filter=Q(computadores__anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], computadores__anomalias__ativo=True),
            distinct=True
        ),
        num_anomalias_diretas=Count(
            'anomalias',
            filter=Q(anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], anomalias__ativo=True),
            distinct=True
        )
    ).annotate(
        num_anomalias=F('num_anomalias_computador') + F('num_anomalias_diretas')
    ).filter(num_anomalias__gt=0).order_by('-num_anomalias')[:5]

    computadores_problematicos = Computador.objects.annotate(
        num_anomalias=Count(
            'anomalias',
            filter=Q(anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], anomalias__ativo=True)
        )
    ).filter(num_anomalias__gt=0).order_by('-num_anomalias')[:5]

    estados = dict(Anomalia.ESTADO_CHOICES)
    dados_estado = {
        estado: Anomalia.objects.filter(estado=estado).count()
        for estado in estados
    }

    context = {
        'total_salas': total_salas,
        'total_computadores': total_computadores,
        'total_anomalias': total_anomalias,
        'anomalias_por_estado': anomalias_por_estado,
        'anomalias_recentes': anomalias_recentes,
        'salas_problematicas': salas_problematicas,
        'computadores_problematicos': computadores_problematicos,
        'dados_estado_labels': list(estados.values()),
        'dados_estado_valores': list(dados_estado.values()),
        'dados_estado_cores': ["#ff5858", "#68c2ff", "#7affb2"],
    }

    return render(request, 'dashboard/index.html', context)


@login_required
@user_passes_test(is_coordenador)
def coordinator_dashboard(request):
    salas = filter_salas_for_user(Sala.objects.all(), request.user)
    computadores = filter_computadores_for_user(
        Computador.objects.select_related("sala"),
        request.user,
    )
    anomalias = filter_anomalias_for_user(
        Anomalia.objects.filter(ativo=True).select_related(
            "sala",
            "computador",
            "computador__sala",
            "reportado_por",
        ),
        request.user,
    )

    anomalias_por_estado = [
        {
            "estado": estado,
            "label": label,
            "total": anomalias.filter(estado=estado).count(),
        }
        for estado, label in Anomalia.ESTADO_CHOICES
    ]

    anomalias_por_sala = (
        salas.annotate(
            num_anomalias_computador=Count(
                "computadores__anomalias",
                filter=Q(computadores__anomalias__ativo=True),
                distinct=True,
            ),
            num_anomalias_diretas=Count(
                "anomalias",
                filter=Q(anomalias__ativo=True),
                distinct=True,
            ),
        )
        .annotate(num_anomalias=F("num_anomalias_computador") + F("num_anomalias_diretas"))
        .order_by("-num_anomalias", "numero")
    )

    anomalias_recentes = anomalias.order_by("-data_registo")[:5]

    context = {
        "total_salas": salas.count(),
        "total_computadores": computadores.count(),
        "total_pendentes": anomalias.filter(estado="PENDENTE").count(),
        "total_em_resolucao": anomalias.filter(estado="EM_RESOLUCAO").count(),
        "total_resolvidas": anomalias.filter(estado="RESOLVIDO").count(),
        "anomalias_recentes": anomalias_recentes,
        "anomalias_por_estado": anomalias_por_estado,
        "anomalias_por_sala": anomalias_por_sala,
        "estado_chart_labels": [item["label"] for item in anomalias_por_estado],
        "estado_chart_values": [item["total"] for item in anomalias_por_estado],
        "estado_chart_colors": ["#ffc107", "#17a2b8", "#28a745"],
        "salas_chart_labels": [sala.numero for sala in anomalias_por_sala],
        "salas_chart_values": [sala.num_anomalias for sala in anomalias_por_sala],
    }
    return render(request, "dashboard/coordinator.html", context)


@login_required
def grafico_anomalias_estado(request):
    dados = (
        filter_anomalias_for_user(Anomalia.objects.all(), request.user)
        .values('estado')
        .annotate(total=Count('estado'))
    )

    labels = []
    valores = []
    cores = []

    CORES_ESTADOS = {
        'PENDENTE': '#ffc107',
        'EM_RESOLUCAO': '#17a2b8',
        'RESOLVIDO': '#28a745',
    }

    for item in dados:
        labels.append(dict(Anomalia.ESTADO_CHOICES)[item['estado']])
        valores.append(item['total'])
        cores.append(CORES_ESTADOS.get(item['estado'], '#6c757d'))

    context = {
        'labels': labels,
        'valores': valores,
        'cores': cores,
    }
    return render(request, 'anomalias/grafico_estado.html', context)
