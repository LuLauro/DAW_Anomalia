import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from anomalias.models import Anomalia
from auditoria.services import log_action
from users.access import filter_anomalias_for_user
from .services import AIAgentService


def _is_tecnico(user):
    return user.groups.filter(name="Tecnico").exists()


def _normalize_conversation_history(raw_history):
    if not isinstance(raw_history, list):
        return []

    history = []
    for item in raw_history[-8:]:
        if not isinstance(item, dict):
            continue

        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()

        if role not in {"user", "bot"} or not content:
            continue

        history.append({"role": role, "content": content[:1200]})

    return history


def _build_assistant_context_message(anomalia):
    sala = "-"
    if anomalia.sala:
        sala = anomalia.sala.numero
    elif anomalia.computador and anomalia.computador.sala:
        sala = anomalia.computador.sala.numero

    computador = (
        anomalia.computador.numero_identificacao if anomalia.computador else "-"
    )
    tipo = anomalia.get_tipo_display() if anomalia.tipo else "-"

    return "\n".join(
        [
            "Quero continuar a analisar esta anomalia.",
            f"Título: {anomalia.titulo}",
            f"Descrição: {anomalia.descricao}",
            f"Tipo: {tipo}",
            f"Prioridade: {anomalia.get_prioridade_display()}",
            f"Sala: {sala}",
            f"Computador: {computador}",
            f"Estado: {anomalia.get_estado_display()}",
            "Ajuda-me a aprofundar o diagnóstico e os próximos passos.",
        ]
    )


@login_required
@require_POST
def perguntar(request):
    if not _is_tecnico(request.user):
        return JsonResponse({"error": "Não posso responder a isso."}, status=403)

    pergunta = (request.POST.get("pergunta") or "").strip()
    if not pergunta:
        return JsonResponse({"error": "Não posso responder a isso."}, status=400)

    anomalias = (
        Anomalia.objects.filter(ativo=True)
        .select_related("sala", "computador", "computador__sala")
        .order_by("data_registo")
    )

    service = AIAgentService()
    resposta = service.analyze(pergunta, list(anomalias))
    log_action(
        request=request,
        action="UTILIZAR_ASSISTENTE_IA",
        entity="Assistente IA",
        description=f"Pergunta enviada ao assistente IA: {pergunta[:200]}",
    )
    return JsonResponse(resposta, safe=True)


@login_required
@require_POST
def chat(request):
    if not _is_tecnico(request.user):
        return JsonResponse({"error": "Não autorizado."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Pedido inválido."}, status=400)

    pergunta = (payload.get("message") or "").strip()
    conversation = _normalize_conversation_history(payload.get("conversation"))

    if not pergunta:
        return JsonResponse({"error": "A mensagem é obrigatória."}, status=400)

    anomalias = (
        Anomalia.objects.filter(ativo=True)
        .select_related("sala", "computador", "computador__sala")
    )

    service = AIAgentService()

    resposta = service.analyze(
        pergunta,
        list(anomalias),
        conversation_history=conversation,
    )
    log_action(
        request=request,
        action="UTILIZAR_ASSISTENTE_IA",
        entity="Assistente IA",
        description=f"Mensagem enviada ao assistente IA: {pergunta[:200]}",
    )
    return JsonResponse(resposta)


@login_required
@require_GET
def diagnostico_anomalia(request, pk):
    anomalias = filter_anomalias_for_user(
        Anomalia.objects.select_related("sala", "computador", "computador__sala"),
        request.user,
    )
    anomalia = get_object_or_404(anomalias, pk=pk)

    service = AIAgentService()
    resposta = service.diagnose_anomaly(anomalia, list(anomalias))
    log_action(
        request=request,
        action="UTILIZAR_DIAGNOSTICO_IA",
        entity=anomalia,
        description=f"Diagnóstico IA gerado para a anomalia '{anomalia.titulo}'.",
    )

    return JsonResponse(
        {
            "response": resposta,
            "assistant_context_message": _build_assistant_context_message(anomalia),
        }
    )


@login_required
def agente_ui(request):
    if not _is_tecnico(request.user):
        return JsonResponse({"error": "Não posso responder a isso."}, status=403)
    return render(request, "ai_agent/tecnico_agent.html")
