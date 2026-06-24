from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Count, Q, F, Subquery, OuterRef
from django.utils import timezone
from datetime import timedelta
from salas.models import Sala
from computadores.models import Computador
from anomalias.models import Anomalia
from django.contrib.auth import logout
from django.contrib import messages
from users.permissions import is_admin

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Logout realizado com sucesso!')
    return redirect('index')



    
@user_passes_test(is_admin)
def dashboard(request):
    # Contagem de anomalias agrupadas por estado (PENDENTE, EM_RESOLUCAO, RESOLVIDO)
    total_salas = Sala.objects.count()
    total_computadores = Computador.objects.count()
    total_anomalias = Anomalia.objects.count()

    # Anomalias por estado
    anomalias_por_estado = Anomalia.objects.values(
        'estado').annotate(total=Count('id'))

    # Filtra as anomalias registradas nos últimos 7 dias (recentes)
    data_limite = timezone.now() - timedelta(days=7)
    anomalias_recentes = Anomalia.objects.filter(
        data_registo__gte=data_limite
    ).order_by('-data_registo')[:5]

    # Salas com mais anomalias
    salas_problematicas = Sala.objects.annotate(
        num_anomalias_computador=Count(
            'computadores__anomalias',
            filter=Q(computadores__anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], computadores__anomalias__ativo=True),
            distinct=True  
        ),
        num_anomalias_diretas=Count(
            'anomalias',
            filter=Q(anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], anomalias__ativo=True),
            distinct=True  # para garantir que não duplica por joins
        )
    ).annotate(
        num_anomalias=F('num_anomalias_computador') + F('num_anomalias_diretas')
    ).filter(num_anomalias__gt=0).order_by('-num_anomalias')[:5]
    
    # Computadores com mais anomalias
    computadores_problematicos = Computador.objects.annotate(
        num_anomalias=Count(
            'anomalias',
            filter=Q(anomalias__estado__in=['PENDENTE', 'EM_RESOLUCAO'], anomalias__ativo=True)
        )
    ).filter(num_anomalias__gt=0).order_by('-num_anomalias')[:5]
    
    # Dados para o gráfico de pizza
    estados = dict(Anomalia.ESTADO_CHOICES)
    dados_estado = {
        estado: Anomalia.objects.filter(estado=estado).count()
        for estado in estados
    }
# Monta o contexto que será enviado para o template do dashboard
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
        'dados_estado_cores': ["#ff5858", "#68c2ff", "#7affb2"],  # customize as cores
    }

    return render(request, 'dashboard/index.html', context)

@login_required
def grafico_anomalias_estado(request):
# Consulta agregada de contagem por estado
    dados = (
        Anomalia.objects
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
# Prepara os dados para o gráfico
    for item in dados:
        labels.append(dict(Anomalia.ESTADO_CHOICES)[item['estado']])  # label amigável
        valores.append(item['total']) # total de anomalias neste estado
        cores.append(CORES_ESTADOS.get(item['estado'], '#6c757d'))  # cor padrão cinza

# Envia os dados para o template do gráfico
    context = {
        'labels': labels,
        'valores': valores,
        'cores': cores,
    }
    return render(request, 'anomalias/grafico_estado.html', context)