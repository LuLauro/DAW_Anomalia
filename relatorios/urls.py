from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.relatorio_form, name="form"),
    path("pdf/", views.gerar_relatorio_pdf, name="gerar_pdf"),
    path("semanal/", views.relatorio_semanal_pdf, name="relatorio_semanal_pdf"),
]
