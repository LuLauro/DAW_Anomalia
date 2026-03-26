from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from anomalias.models import Anomalia


class AIAgentTests(TestCase):
    def setUp(self):
        self.group_tecnico = Group.objects.create(name="Tecnico")
        self.group_professor = Group.objects.create(name="Professor")

        self.tecnico = User.objects.create_user(username="tec", password="pass")
        self.tecnico.groups.add(self.group_tecnico)

        self.professor = User.objects.create_user(username="prof", password="pass")
        self.professor.groups.add(self.group_professor)

        self.anomalia = Anomalia.objects.create(
            titulo="Teste",
            descricao="Desc",
            estado="PENDENTE",
            data_registo=timezone.now(),
            reportado_por=self.professor,
        )

    def test_tecnico_ok(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:perguntar")

        with mock.patch("ai_agent.services.AIAgentService.analyze") as mocked:
            mocked.return_value = {
                "intent": "resumo",
                "pendentes": 1,
                "em_resolucao": 0,
                "resolvidas": 0,
            }
            response = self.client.post(url, {"pergunta": "Resumo do estado atual"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "resumo")

    def test_non_tecnico_denied(self):
        self.client.login(username="prof", password="pass")
        url = reverse("ai_agent:perguntar")
        response = self.client.post(url, {"pergunta": "Resumo do estado atual"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_invalid_question(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:perguntar")
        response = self.client.post(url, {"pergunta": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
