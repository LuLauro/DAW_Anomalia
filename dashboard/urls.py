from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('dashboard/', views.grafico_anomalias_estado, name='grafico_anomalias_estado'),
]
