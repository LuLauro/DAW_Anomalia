from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from computadores.models import Computador
from salas.models import Sala

from .models import Anomalia
from .utils import (
    get_email_recipients_for_new_anomaly,
    get_email_recipients_for_status_change,
)


class CoordinatorAccessRestrictionTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Coordenador")
        self.coordinator = User.objects.create_user(
            username="coord",
            password="secret123",
        )
        self.coordinator.groups.add(self.group)

        self.other_user = User.objects.create_user(
            username="other",
            password="secret123",
        )

        self.assigned_room = Sala.objects.create(
            numero="C2.3",
            coordinator=self.coordinator,
        )
        self.foreign_room = Sala.objects.create(
            numero="C2.9",
            coordinator=self.other_user,
        )

        self.assigned_computer = Computador.objects.create(
            numero_identificacao="PC-01",
            sala=self.assigned_room,
            marca="Dell",
            modelo="Optiplex",
        )
        self.foreign_computer = Computador.objects.create(
            numero_identificacao="PC-99",
            sala=self.foreign_room,
            marca="HP",
            modelo="EliteDesk",
        )

        self.assigned_anomalia = Anomalia.objects.create(
            titulo="Assigned",
            descricao="Assigned room anomaly",
            computador=self.assigned_computer,
            reportado_por=self.other_user,
        )
        self.foreign_anomalia = Anomalia.objects.create(
            titulo="Foreign",
            descricao="Foreign room anomaly",
            computador=self.foreign_computer,
            reportado_por=self.other_user,
        )

        self.client.force_login(self.coordinator)

    def test_coordinator_only_sees_assigned_rooms(self):
        response = self.client.get(reverse("salas:lista_salas"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["salas"].order_by("id"),
            [self.assigned_room],
            transform=lambda sala: sala,
        )

    def test_coordinator_cannot_access_foreign_room_detail(self):
        response = self.client.get(
            reverse("salas:detalhe_sala", args=[self.foreign_room.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_coordinator_only_sees_assigned_computers(self):
        response = self.client.get(reverse("computadores:lista_computadores"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["computadores"].order_by("id"),
            [self.assigned_computer],
            transform=lambda computador: computador,
        )

    def test_coordinator_cannot_access_foreign_computer_detail(self):
        response = self.client.get(
            reverse("computadores:detalhe_computador", args=[self.foreign_computer.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_coordinator_only_sees_assigned_anomalies(self):
        response = self.client.get(reverse("anomalias:lista_anomalias"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["anomalias"].order_by("id"),
            [self.assigned_anomalia],
            transform=lambda anomalia: anomalia,
        )

    def test_coordinator_cannot_access_foreign_anomaly_detail(self):
        response = self.client.get(
            reverse("anomalias:detalhe_anomalia", args=[self.foreign_anomalia.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_coordinator_cannot_load_foreign_room_computers_via_ajax(self):
        response = self.client.get(
            reverse("anomalias:computadores_por_sala"),
            {"sala_id": self.foreign_room.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"computadores": []})


class PriorityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="prof",
            password="secret123",
        )
        self.sala = Sala.objects.create(numero="A1.1")
        self.computador = Computador.objects.create(
            numero_identificacao="PC-10",
            sala=self.sala,
            marca="Dell",
            modelo="Optiplex",
        )
        self.client.force_login(self.user)

    def test_priority_defaults_to_media(self):
        anomalia = Anomalia.objects.create(
            titulo="Sem prioridade explícita",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
        )

        self.assertEqual(anomalia.prioridade, "MEDIA")

    def test_filter_by_priority(self):
        alta = Anomalia.objects.create(
            titulo="Alta",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="ALTA",
        )
        Anomalia.objects.create(
            titulo="Baixa",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="BAIXA",
        )

        response = self.client.get(
            reverse("anomalias:lista_anomalias"),
            {"prioridade": "ALTA"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["anomalias"],
            [alta],
            transform=lambda anomalia: anomalia,
        )

    def test_order_by_priority(self):
        critica = Anomalia.objects.create(
            titulo="Crítica",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="CRITICA",
        )
        alta = Anomalia.objects.create(
            titulo="Alta",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="ALTA",
        )
        media = Anomalia.objects.create(
            titulo="Média",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="MEDIA",
        )

        response = self.client.get(
            reverse("anomalias:lista_anomalias"),
            {"ordenacao": "prioridade"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["anomalias"][:3]),
            [critica, alta, media],
        )

    def test_cannot_change_priority_after_resolution(self):
        anomalia = Anomalia.objects.create(
            titulo="Resolvida",
            descricao="Teste",
            computador=self.computador,
            reportado_por=self.user,
            prioridade="MEDIA",
            estado="RESOLVIDO",
        )

        response = self.client.post(
            reverse("anomalias:atualizar_prioridade", args=[anomalia.pk]),
            {"prioridade": "CRITICA"},
            follow=True,
        )

        anomalia.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(anomalia.prioridade, "MEDIA")


class EmailRecipientRulesTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Administrador")
        self.coordinator_group = Group.objects.create(name="Coordenador")
        self.professor_group = Group.objects.create(name="Professor")
        self.tecnico_group = Group.objects.create(name="Tecnico")

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="secret123",
            is_staff=True,
        )
        self.admin.groups.add(self.admin_group)

        self.other_admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="secret123",
        )
        self.other_admin.groups.add(self.admin_group)

        self.coordinator = User.objects.create_user(
            username="coord",
            email="coord@example.com",
            password="secret123",
        )
        self.coordinator.groups.add(self.coordinator_group)

        self.professor = User.objects.create_user(
            username="prof",
            email="prof@example.com",
            password="secret123",
        )
        self.professor.groups.add(self.professor_group)

        self.tecnico = User.objects.create_user(
            username="tec",
            email="tec@example.com",
            password="secret123",
        )
        self.tecnico.groups.add(self.tecnico_group)

        self.room = Sala.objects.create(numero="A1.1", coordinator=self.coordinator)
        self.computer = Computador.objects.create(
            numero_identificacao="PC-1",
            sala=self.room,
            marca="Dell",
            modelo="Optiplex",
        )

    def test_professor_new_anomaly_notifies_admins_and_room_coordinator_only(self):
        anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Teste",
            computador=self.computer,
            reportado_por=self.professor,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.professor)

        self.assertCountEqual(
            recipients,
            ["admin@example.com", "admin2@example.com", "coord@example.com"],
        )
        self.assertNotIn("prof@example.com", recipients)
        self.assertNotIn("tec@example.com", recipients)

    def test_coordinator_new_anomaly_notifies_only_admins(self):
        anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Teste",
            computador=self.computer,
            reportado_por=self.coordinator,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.coordinator)

        self.assertCountEqual(recipients, ["admin@example.com", "admin2@example.com"])
        self.assertNotIn("coord@example.com", recipients)

    def test_admin_new_anomaly_notifies_only_coordinator(self):
        anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Teste",
            computador=self.computer,
            reportado_por=self.admin,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.admin)

        self.assertEqual(recipients, ["coord@example.com"])
        self.assertNotIn("admin@example.com", recipients)

    def test_new_anomaly_without_room_notifies_only_admins(self):
        anomalia = Anomalia.objects.create(
            titulo="Geral",
            descricao="Sem sala",
            reportado_por=self.professor,
            sala=None,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.professor)

        self.assertCountEqual(recipients, ["admin@example.com", "admin2@example.com"])

    def test_new_anomaly_with_room_without_coordinator_notifies_only_admins(self):
        room_without_coordinator = Sala.objects.create(numero="B2.1")
        computer_without_coordinator = Computador.objects.create(
            numero_identificacao="PC-2",
            sala=room_without_coordinator,
            marca="HP",
            modelo="EliteDesk",
        )
        anomalia = Anomalia.objects.create(
            titulo="Sem coordenador",
            descricao="Teste",
            computador=computer_without_coordinator,
            reportado_por=self.admin,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.admin)

        self.assertEqual(recipients, ["admin2@example.com"])

    def test_status_change_notifies_admins_coordinator_and_reporter_except_actor(self):
        anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Teste",
            computador=self.computer,
            reportado_por=self.professor,
        )

        recipients = get_email_recipients_for_status_change(anomalia, self.admin)

        self.assertCountEqual(recipients, ["admin2@example.com", "coord@example.com", "prof@example.com"])
        self.assertNotIn("admin@example.com", recipients)
        self.assertNotIn("tec@example.com", recipients)

    def test_missing_email_and_duplicates_are_ignored(self):
        self.other_admin.email = ""
        self.other_admin.save(update_fields=["email"])
        self.coordinator.email = "admin@example.com"
        self.coordinator.save(update_fields=["email"])

        anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Teste",
            computador=self.computer,
            reportado_por=self.professor,
        )

        recipients = get_email_recipients_for_new_anomaly(anomalia, self.professor)

        self.assertEqual(recipients, ["admin@example.com"])
