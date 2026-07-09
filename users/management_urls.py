from django.urls import path

from .views import (
    alterar_estado_utilizador,
    editar_utilizador,
    lista_utilizadores,
    novo_utilizador,
)

app_name = "user_management"

urlpatterns = [
    path("utilizadores/", lista_utilizadores, name="lista_utilizadores"),
    path("utilizadores/novo/", novo_utilizador, name="novo_utilizador"),
    path("utilizadores/<int:user_id>/editar/", editar_utilizador, name="editar_utilizador"),
    path("utilizadores/<int:user_id>/estado/", alterar_estado_utilizador, name="alterar_estado_utilizador"),
]
