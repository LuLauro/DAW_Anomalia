from django.urls import path

from . import views

app_name = "tecnico"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("anomalias/", views.lista_anomalias, name="lista_anomalias"),
    path("anomalias/historico/", views.historico_anomalias, name="historico_anomalias"),
    path("anomalias/<int:pk>/", views.detalhe_anomalia, name="detalhe_anomalia"),
    path("anomalias/<int:pk>/estado/", views.atualizar_estado, name="atualizar_estado"),
    path(
        "anomalias/<int:pk>/observacoes/",
        views.adicionar_observacao,
        name="adicionar_observacao",
    ),
]
