from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.relatorio_form, name="form"),
    path("qrcodes/", views.qrcode_kit_form, name="qrcode_kit_form"),
    path("qrcodes/pdf/", views.qrcode_kit_pdf, name="qrcode_kit_pdf"),
    path("pdf/", views.gerar_relatorio_pdf, name="gerar_pdf"),
    path("semanal/", views.relatorio_semanal_pdf, name="relatorio_semanal_pdf"),
]
