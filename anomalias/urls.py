from django.urls import path
from . import views

app_name = 'anomalias'

urlpatterns = [
    
    path('', views.lista_anomalias, name='lista_anomalias'),
    path('registar/', views.registar_anomalia, name='registar_anomalia'),
    path('detalhe/<int:pk>/', views.detalhe_anomalia, name='detalhe_anomalia'),
    path('anexo/<int:pk>/', views.ver_anexo, name='ver_anexo'),
    path('atualizar-estado/<int:pk>/', views.atualizar_estado, name='atualizar_estado'),
    path('observacoes/<int:pk>/', views.adicionar_observacao, name='adicionar_observacao'),
    path('historico/', views.historico_anomalias, name='historico_anomalias'),
    path('eliminar/<int:pk>/', views.eliminar_anomalia, name='eliminar_anomalia'),
    path('nova-geral/', views.registar_anomalia_geral, name='registar_anomalia_geral'),
    path('computadores-por-sala/', views.computadores_por_sala, name='computadores_por_sala'),
    
]
