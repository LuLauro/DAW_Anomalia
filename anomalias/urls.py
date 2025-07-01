from django.urls import path
from . import views

app_name = 'anomalias'

urlpatterns = [
    
    path('', views.lista_anomalias, name='lista_anomalias'),
    path('registar/', views.registar_anomalia, name='registar_anomalia'),
    path('atualizar-estado/<int:pk>/', views.atualizar_estado, name='atualizar_estado'),
    path('observacoes/<int:pk>/', views.adicionar_observacao, name='adicionar_observacao'),
    path('historico/', views.historico_anomalias, name='historico_anomalias'),
    path('eliminar/<int:pk>/', views.eliminar_anomalia, name='eliminar_anomalia'),
    path('nova-geral/', views.registar_anomalia_geral, name='registar_anomalia_geral'),
    path('teste-email/', views.teste_email, name='teste_email'),

]
