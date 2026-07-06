import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from anomalias.models import Anomalia
from .services import AIAgentService


def _is_tecnico(user):
    return user.groups.filter(name="Tecnico").exists()


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

    if not pergunta:
        return JsonResponse({"error": "A mensagem é obrigatória."}, status=400)

    anomalias = (
        Anomalia.objects.filter(ativo=True)
        .select_related("sala", "computador", "computador__sala")
    )

    service = AIAgentService()

    resposta = service.analyze(
        pergunta,
        list(anomalias)
    )
    return JsonResponse(resposta)

@login_required
def agente_ui(request):
    if not _is_tecnico(request.user):
        return JsonResponse({"error": "Não posso responder a isso."}, status=403)
    return render(request, "ai_agent/tecnico_agent.html")
