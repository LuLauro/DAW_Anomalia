from django.urls import path

from .views import lista_logs

app_name = "auditoria"

urlpatterns = [
    path("", lista_logs, name="lista_logs"),
]

