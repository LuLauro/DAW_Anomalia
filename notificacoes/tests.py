from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from anomalias.models import Anomalia
from computadores.models import Computador
from salas.models import Sala

from .models import Notification


class CoordinatorNotificationScopeTests(TestCase):
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
            titulo="Assigned anomaly",
            descricao="Assigned",
            computador=self.assigned_computer,
            reportado_por=self.other_user,
        )
        self.foreign_anomalia = Anomalia.objects.create(
            titulo="Foreign anomaly",
            descricao="Foreign",
            computador=self.foreign_computer,
            reportado_por=self.other_user,
        )

        anomalia_content_type = ContentType.objects.get_for_model(Anomalia)
        self.visible_notification = Notification.objects.create(
            recipient=self.coordinator,
            notification_type="nova_anomalia",
            title="Visible",
            message="Visible",
            content_type=anomalia_content_type,
            object_id=self.assigned_anomalia.id,
        )
        self.hidden_notification = Notification.objects.create(
            recipient=self.coordinator,
            notification_type="nova_anomalia",
            title="Hidden",
            message="Hidden",
            content_type=anomalia_content_type,
            object_id=self.foreign_anomalia.id,
        )

        self.client.force_login(self.coordinator)

    def test_coordinator_only_sees_notifications_for_assigned_rooms(self):
        response = self.client.get(reverse("notificacoes:list"))

        self.assertEqual(response.status_code, 200)
        notifications = list(response.context["notifications"])
        self.assertIn(self.visible_notification, notifications)
        self.assertNotIn(self.hidden_notification, notifications)
        self.assertTrue(
            all(
                notification.object_id != self.foreign_anomalia.id
                for notification in notifications
            )
        )

    def test_coordinator_cannot_mark_foreign_notification_as_read(self):
        response = self.client.get(
            reverse("notificacoes:mark_as_read", args=[self.hidden_notification.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_unread_count_ignores_foreign_room_notifications(self):
        visible_count = Notification.objects.filter(
            recipient=self.coordinator,
            object_id=self.assigned_anomalia.id,
            is_read=False,
        ).count()
        self.assertEqual(Notification.unread_count(self.coordinator), visible_count)
