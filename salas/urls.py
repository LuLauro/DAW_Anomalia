from django.urls import path
from . import views

app_name = 'salas'

urlpatterns = [
    path('', views.lista_salas, name='lista_salas'),
    path('registar/', views.registar_sala, name='registar_sala'),
    path('<int:pk>/', views.detalhe_sala, name='detalhe_sala'),
]
