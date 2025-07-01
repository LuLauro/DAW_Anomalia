from django.urls import path
from . import views

app_name = 'computadores'

urlpatterns = [
    path('', views.lista_computadores, name='lista_computadores'),
    path('registar/', views.registar_computador, name='registar_computador'),
    path('<int:pk>/', views.detalhe_computador, name='detalhe_computador'),
]
