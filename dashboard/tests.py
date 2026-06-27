from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from anomalias.models import Anomalia
from computadores.models import Computador
from salas.models import Sala


class CoordinatorDashboardTests(TestCase):
    def setUp(self):
        self.coordinator_group = Group.objects.create(name="Coordenador")
        self.coordinator = User.objects.create_user(
            username="coord",
            password="secret123",
        )
        self.coordinator.groups.add(self.coordinator_group)

        self.other_user = User.objects.create_user(
            username="other",
            password="secret123",
        )

        self.assigned_room = Sala.objects.create(
            numero="C2.3",
            coordinator=self.coordinator,
        )
        self.other_room = Sala.objects.create(
            numero="C2.9",
            coordinator=self.other_user,
        )

        self.assigned_computer = Computador.objects.create(
            numero_identificacao="PC-01",
            sala=self.assigned_room,
            marca="Dell",
            modelo="Optiplex",
        )
        self.other_computer = Computador.objects.create(
            numero_identificacao="PC-99",
            sala=self.other_room,
            marca="HP",
            modelo="EliteDesk",
        )

        Anomalia.objects.create(
            titulo="Pending assigned",
            descricao="Pending",
            computador=self.assigned_computer,
            reportado_por=self.other_user,
            estado="PENDENTE",
        )
        Anomalia.objects.create(
            titulo="In progress assigned",
            descricao="In progress",
            computador=self.assigned_computer,
            reportado_por=self.other_user,
            estado="EM_RESOLUCAO",
        )
        Anomalia.objects.create(
            titulo="Resolved assigned",
            descricao="Resolved",
            computador=self.assigned_computer,
            reportado_por=self.other_user,
            estado="RESOLVIDO",
        )
        Anomalia.objects.create(
            titulo="Foreign anomaly",
            descricao="Foreign",
            computador=self.other_computer,
            reportado_por=self.other_user,
            estado="PENDENTE",
        )

        self.client.force_login(self.coordinator)

    def test_coordinator_login_redirects_to_dedicated_dashboard(self):
        anonymous_client = Client()
        response = anonymous_client.post(
            reverse("users:login"),
            {"username": "coord", "password": "secret123"},
        )

        self.assertRedirects(response, reverse("dashboard:coordinator"))

    def test_coordinator_dashboard_only_uses_assigned_room_data(self):
        response = self.client.get(reverse("dashboard:coordinator"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_salas"], 1)
        self.assertEqual(response.context["total_computadores"], 1)
        self.assertEqual(response.context["total_pendentes"], 1)
        self.assertEqual(response.context["total_em_resolucao"], 1)
        self.assertEqual(response.context["total_resolvidas"], 1)

        salas_chart = list(response.context["anomalias_por_sala"])
        self.assertEqual(len(salas_chart), 1)
        self.assertEqual(salas_chart[0].numero, self.assigned_room.numero)
        self.assertEqual(salas_chart[0].num_anomalias, 3)

        recentes = list(response.context["anomalias_recentes"])
        self.assertEqual(len(recentes), 3)
        self.assertTrue(all(item.computador.sala_id == self.assigned_room.id for item in recentes))
