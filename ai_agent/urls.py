from django.urls import path

from . import views

app_name = "ai_agent"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("perguntar/", views.perguntar, name="perguntar"),
    path(
        "diagnostico-anomalia/<int:pk>/",
        views.diagnostico_anomalia,
        name="diagnostico_anomalia",
    ),
    path("", views.agente_ui, name="ui"),
]
