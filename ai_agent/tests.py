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

    def test_chat_endpoint_returns_service_response(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:chat")

        with mock.patch("ai_agent.services.AIAgentService.analyze") as mocked:
            mocked.return_value = {"response": "Resposta placeholder"}
            response = self.client.post(
                url,
                data='{"message": "Resumo desta semana"}',
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Resposta placeholder")

    def test_chat_endpoint_passes_conversation_history(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:chat")

        with mock.patch("ai_agent.services.AIAgentService.analyze") as mocked:
            mocked.return_value = {"response": "Resposta"}
            self.client.post(
                url,
                data=(
                    '{"message": "E os outros?", "conversation": '
                    '[{"role": "user", "content": "Existem equipamentos com muitas avarias?"}, '
                    '{"role": "bot", "content": "O Computador 15 tem 4 anomalias."}]}'
                ),
                content_type="application/json",
            )

        mocked.assert_called_once()
        self.assertEqual(
            mocked.call_args.kwargs["conversation_history"],
            [
                {
                    "role": "user",
                    "content": "Existem equipamentos com muitas avarias?",
                },
                {"role": "bot", "content": "O Computador 15 tem 4 anomalias."},
            ],
        )

    def test_chat_endpoint_rejects_non_tecnico(self):
        self.client.login(username="prof", password="pass")
        url = reverse("ai_agent:chat")
        response = self.client.post(
            url,
            data='{"message": "Resumo desta semana"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_chat_endpoint_requires_message(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:chat")
        response = self.client.post(
            url,
            data='{"message": ""}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_diagnostico_anomalia_returns_response(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:diagnostico_anomalia", args=[self.anomalia.pk])

        with mock.patch("ai_agent.services.AIAgentService.diagnose_anomaly") as mocked:
            mocked.return_value = "## Possíveis causas\n- Cabo solto"
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["response"],
            "## Possíveis causas\n- Cabo solto",
        )
        self.assertIn("assistant_context_message", response.json())

    def test_diagnostico_anomalia_uses_fallback_when_service_fails(self):
        self.client.login(username="tec", password="pass")
        url = reverse("ai_agent:diagnostico_anomalia", args=[self.anomalia.pk])

        with mock.patch(
            "ai_agent.services.AIAgentService._call_api",
            side_effect=RuntimeError("API indisponível"),
        ):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tempo estimado", response.json()["response"])

    def test_diagnostico_anomalia_filters_professor_access(self):
        other_professor = User.objects.create_user(username="prof2", password="pass")
        other_professor.groups.add(self.group_professor)

        self.client.login(username="prof", password="pass")
        url = reverse("ai_agent:diagnostico_anomalia", args=[self.anomalia.pk])
        with mock.patch("ai_agent.services.AIAgentService.diagnose_anomaly") as mocked:
            mocked.return_value = "## Possíveis causas\n- Cabo solto"
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.login(username="prof2", password="pass")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
