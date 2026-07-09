from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from anomalias.models import Perfil
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


class UserManagementViewsTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Administrador")
        self.professor_group = Group.objects.create(name="Professor")
        self.coordinator_group = Group.objects.create(name="Coordenador")
        self.tecnico_group = Group.objects.create(name="Tecnico")

        self.admin_user = User.objects.create_user(
            username="admin-ui",
            password="secret123",
            is_staff=True,
        )
        self.admin_user.groups.add(self.admin_group)

        self.professor_user = User.objects.create_user(
            username="prof-ui",
            password="secret123",
        )
        self.professor_user.groups.add(self.professor_group)

    def test_admin_can_open_user_list(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("user_management:lista_utilizadores"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestão de Utilizadores")

    def test_non_admin_is_redirected_from_user_list(self):
        self.client.force_login(self.professor_user)

        response = self.client.get(reverse("user_management:lista_utilizadores"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("anomalias:lista_anomalias"))

    def test_create_user_assigns_group_and_profiles(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("user_management:novo_utilizador"),
            {
                "nome": "Coordenador Teste",
                "username": "coord-ui",
                "email": "coord@example.com",
                "password": "secret12345",
                "confirm_password": "secret12345",
                "perfil": "Coordenador",
                "estado": "ativo",
            },
        )

        self.assertRedirects(response, reverse("user_management:lista_utilizadores"))
        user = User.objects.get(username="coord-ui")
        self.assertTrue(user.groups.filter(name="Coordenador").exists())
        self.assertTrue(PerfilCoordenador.objects.filter(user=user).exists())
        self.assertEqual(Perfil.objects.get(user=user).tipo, "COORD")

    def test_create_tecnico_user_creates_legacy_profile(self):
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("user_management:novo_utilizador"),
            {
                "nome": "Tecnico Teste",
                "username": "tec-ui",
                "email": "tec@example.com",
                "password": "secret12345",
                "confirm_password": "secret12345",
                "perfil": "Tecnico",
                "estado": "ativo",
            },
        )

        user = User.objects.get(username="tec-ui")
        self.assertEqual(Perfil.objects.get(user=user).tipo, "TEC")
        self.assertFalse(user.is_staff)

    def test_edit_user_keeps_password_when_blank(self):
        target_user = User.objects.create_user(
            username="edit-me",
            password="old-secret-123",
            first_name="Nome",
        )
        target_user.groups.add(self.professor_group)

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("user_management:editar_utilizador", args=[target_user.pk]),
            {
                "nome": "Nome Editado",
                "username": "edit-me",
                "email": "edit@example.com",
                "perfil": "Professor",
                "estado": "ativo",
                "password": "",
                "confirm_password": "",
            },
        )

        self.assertRedirects(response, reverse("user_management:lista_utilizadores"))
        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password("old-secret-123"))
        self.assertEqual(target_user.email, "edit@example.com")

    def test_toggle_user_status_updates_is_active(self):
        target_user = User.objects.create_user(username="toggle-me", password="secret123")
        target_user.groups.add(self.professor_group)

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("user_management:alterar_estado_utilizador", args=[target_user.pk])
        )

        self.assertRedirects(response, reverse("user_management:lista_utilizadores"))
        target_user.refresh_from_db()
        self.assertFalse(target_user.is_active)
