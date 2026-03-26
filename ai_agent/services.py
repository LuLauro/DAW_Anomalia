import json
import urllib.request
from datetime import date

from django.conf import settings
from django.utils import timezone


class AIAgentService:
    """
    Serviço responsável por:
    - construir o prompt do agente restrito
    - enviar o pedido para a API externa
    - validar que a resposta é JSON e respeita o contrato
    """

    ALLOWED_INTENTS = {"tarefas_hoje", "mais_urgente", "resumo"}

    def __init__(self):
        self.api_key = getattr(settings, "AI_AGENT_API_KEY", None)
        self.api_endpoint = getattr(settings, "AI_AGENT_API_ENDPOINT", None)
        self.model = getattr(settings, "AI_AGENT_MODEL", None)

    def build_system_prompt(self):
        return (
            "És um Agente Técnico extremamente restrito. "
            "A tua única função é analisar uma lista de anomalias fornecida em JSON "
            "e responder APENAS a: planeamento diário, prioridade, resumo. "
            "Responde EXCLUSIVAMENTE em JSON. "
            "Não expliques, não comentes, não inventes dados. "
            "Se a pergunta não corresponder a estas intenções, responde apenas com: "
            '{ "error": "Não posso responder a isso." }'
        )

    def _days_open(self, data_registo):
        if not data_registo:
            return 0
        today = timezone.localdate()
        if isinstance(data_registo, date):
            return (today - data_registo).days
        return (today - data_registo.date()).days

    def build_payload(self, pergunta, anomalias):
        context_anomalias = []
        for a in anomalias:
            context_anomalias.append(
                {
                    "id": a.id,
                    "titulo": a.titulo,
                    "estado": a.estado,
                    "data_registo": a.data_registo.date().isoformat(),
                    "sala": a.sala.numero if a.sala else (a.computador.sala.numero if a.computador else None),
                    "computador": a.computador.numero_identificacao if a.computador else None,
                    "tipo": a.tipo,
                    "dias_em_aberto": self._days_open(a.data_registo),
                }
            )

        user_payload = {
            "pergunta": pergunta,
            "anomalias": context_anomalias,
        }

        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.build_system_prompt()},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": 0,
        }

    def _call_api(self, payload):
        if not self.api_key or not self.api_endpoint or not self.model:
            return {"error": "Configuração de IA em falta."}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _extract_content(self, api_response):
        # Compatível com OpenAI-style chat completions
        try:
            return api_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None

    def _validate_json(self, data, allowed_ids):
        if not isinstance(data, dict):
            return {"error": "Não posso responder a isso."}

        if "error" in data:
            return {"error": "Não posso responder a isso."}

        intent = data.get("intent")
        if intent not in self.ALLOWED_INTENTS:
            return {"error": "Não posso responder a isso."}

        if intent == "tarefas_hoje":
            tarefas = data.get("tarefas", [])
            if not isinstance(tarefas, list):
                return {"error": "Não posso responder a isso."}
            for t in tarefas:
                if not isinstance(t, dict):
                    return {"error": "Não posso responder a isso."}
                if t.get("id") not in allowed_ids:
                    return {"error": "Não posso responder a isso."}
            return data

        if intent == "mais_urgente":
            anomalia = data.get("anomalia")
            if not isinstance(anomalia, dict):
                return {"error": "Não posso responder a isso."}
            if anomalia.get("id") not in allowed_ids:
                return {"error": "Não posso responder a isso."}
            return data

        if intent == "resumo":
            for k in ("pendentes", "em_resolucao", "resolvidas"):
                if k not in data:
                    return {"error": "Não posso responder a isso."}
            return data

        return {"error": "Não posso responder a isso."}

    def analyze(self, pergunta, anomalias):
        payload = self.build_payload(pergunta, anomalias)
        api_response = self._call_api(payload)
        content = self._extract_content(api_response)
        if not content:
            return {"error": "Não posso responder a isso."}

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Não posso responder a isso."}

        allowed_ids = {a.id for a in anomalias}
        return self._validate_json(data, allowed_ids)
