from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from salas.models import Sala

from .admin import PerfilCoordenadorAdmin
from .models import PerfilCoordenador


class UserAdminCoordinatorAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="coord", password="secret123")
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret123",
        )
        self.room_a = Sala.objects.create(numero="C2.3")
        self.room_b = Sala.objects.create(numero="C2.5")
        self.room_other = Sala.objects.create(numero="C2.7")

    def test_user_admin_change_page_opens_without_room_field_errors(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:auth_user_change", args=[self.user.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "salas_coordenadas")

    def test_coordinator_profile_admin_uses_horizontal_room_selector(self):
        profile_admin = PerfilCoordenadorAdmin(PerfilCoordenador, admin.site)

        self.assertIn("salas", profile_admin.filter_horizontal)
        self.assertTrue(admin.site.is_registered(PerfilCoordenador))

    def test_profile_assigns_selected_rooms(self):
        profile = PerfilCoordenador.objects.create(user=self.user)

        profile.salas.set([self.room_a, self.room_b])

        self.room_a.refresh_from_db()
        self.room_b.refresh_from_db()
        self.room_other.refresh_from_db()

        self.assertEqual(self.room_a.coordinator, self.user)
        self.assertEqual(self.room_b.coordinator, self.user)
        self.assertIsNone(self.room_other.coordinator)

    def test_profile_removes_unselected_previous_rooms(self):
        profile = PerfilCoordenador.objects.create(user=self.user)
        profile.salas.set([self.room_a, self.room_b])

        profile.salas.set([self.room_b])

        self.room_a.refresh_from_db()
        self.room_b.refresh_from_db()

        self.assertIsNone(self.room_a.coordinator)
        self.assertEqual(self.room_b.coordinator, self.user)
