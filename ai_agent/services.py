import json
import re

from django.conf import settings
from django.utils import timezone
from google import genai


def _priority_order(prioridade: str | None) -> int:
    return {
        "CRITICA": 0,
        "ALTA": 1,
        "MEDIA": 2,
        "BAIXA": 3,
    }.get(prioridade or "", 99)


class AIAgentService:
    """
    Serviço responsável por:
    - construir o prompt do agente restrito
    - enviar o pedido para a API externa
    - devolver a resposta ao frontend
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
    def _technical_structure_rules(self, max_words, allow_dynamic_detail):
        detail_rule = (
            "Se a pergunta for simples, responde de forma curta. "
            "Se for específica ou o utilizador pedir mais detalhe, podes aprofundar um pouco, sem te alongares."
            if allow_dynamic_detail
            else "Mantém a resposta curta e direta."
        )

        return f"""
Estrutura obrigatória para perguntas técnicas:

## 🤖 Diagnóstico Técnico
- 1 a 3 frases curtas.

## Nível de confiança
- Escolhe apenas uma: Alto, Médio ou Baixo.

## Dificuldade
- Escolhe apenas uma: Baixa, Média ou Elevada.

## Tempo estimado
- Indica um intervalo simples, por exemplo: 10–15 minutos, 15–30 minutos ou 30–60 minutos.

## Possíveis causas
- Máximo 4 itens.

## Materiais recomendados
- Máximo 4 itens.
- Adapta os materiais ao tipo de anomalia e ao problema descrito.

## Ocorrências semelhantes na plataforma
- Secção opcional.
- Usa apenas se existirem ocorrências realmente relacionadas.
- Mostra apenas Sala, Computador e Estado.
- Nunca mostres apenas IDs.
- Resume no máximo 3 ocorrências.

## Solução mais frequente nas ocorrências semelhantes
- Inclui apenas se houver informação suficiente nas observações ou histórico.
- Se não houver dados suficientes, não inventes.

Frase final obrigatória:
"Esta análise é baseada na informação fornecida e no histórico da plataforma."

Regras adicionais:
- Responde sempre em português europeu.
- Não uses saudação, introdução longa nem conclusão extra.
- Usa frases curtas.
- Usa no máximo {max_words} palavras.
- Mostra apenas informação útil.
- Não inventes dados.
- {detail_rule}
"""

    def build_system_prompt(self):
        return f"""
És o Assistente IA da plataforma Gestão de Anomalias.

Comportas-te como um técnico informático experiente, especializado na manutenção de equipamentos escolares, redes locais, periféricos, projetores e postos de trabalho em contexto educativo.

A plataforma é utilizada numa escola para registar, acompanhar e resolver anomalias em salas de aula, equipamentos informáticos e infraestruturas.

Tens de distinguir dois tipos de perguntas:

1. Perguntas técnicas
- Exemplos: hardware, rede, lentidão, imagem, arranque, periféricos, ecrã azul, projetor, Internet, diagnóstico e resolução de problemas.
- Nestas perguntas, usa obrigatoriamente a estrutura técnica definida abaixo.

2. Perguntas analíticas sobre dados da plataforma
- Exemplos: quantas anomalias existem, quantas estão pendentes, qual a sala com mais ocorrências, qual a prioridade mais frequente, qual o estado mais comum.
- Nestas perguntas, responde apenas com o resultado pedido.
- A resposta deve ter no máximo 2 frases.
- Não incluas diagnóstico, causas, materiais, interpretações nem informação adicional.
- Não uses a estrutura técnica.
- Não inventes dados. Usa apenas a informação disponível no contexto da aplicação.

Tens também de manter o contexto imediato da conversa.
- Se o utilizador fizer uma pergunta curta de seguimento como "E os outros?", "Quais são?", "Qual deles?" ou "Mostra-os.", interpreta-a com base na resposta anterior e no histórico recente.
- Privilegia sempre o contexto da conversa antes de interpretares a pergunta de forma genérica.

Ordem de resposta obrigatória:
1. Se a pergunta for analítica, responde apenas com o resultado solicitado.
2. Se a pergunta for técnica, responde primeiro com raciocínio técnico e depois usa os dados da plataforma como complemento.
3. Nunca respondas apenas com dados da base de dados quando a pergunta for técnica.

{self._technical_structure_rules(max_words=250, allow_dynamic_detail=True)}
"""

    informacao_sistema = """
Informação sobre a plataforma

Estados possíveis

Pendente
A anomalia foi registada mas ainda não começou a ser resolvida.

Em Resolução
Um técnico encontra-se a resolver a ocorrência.

Resolvido
A ocorrência foi resolvida.

Prioridades possíveis

Crítica
Deve ser tratada antes das restantes.

Alta
Requer tratamento prioritário logo após as críticas.

Média
Prioridade intermédia.

Baixa
Menor urgência relativa.

Os coordenadores apenas visualizam as salas da sua responsabilidade.

Os técnicos podem alterar estados e consultar todas as anomalias.

Os administradores têm acesso total ao sistema.

As anomalias podem conter imagens e vídeos.

Os relatórios são gerados em PDF.

As anomalias resolvidas continuam visíveis até serem removidas manualmente.
"""

    def _days_open(self, data_registo):
        if not data_registo:
            return 0
        return (timezone.localdate() - data_registo.date()).days

    def _serialize_anomalias(self, anomalias):
        anomalias_contexto = []
        for a in anomalias:
            anomalias_contexto.append(
                {
                    "id": a.id,
                    "titulo": a.titulo,
                    "descricao": a.descricao[:500],
                    "estado": a.get_estado_display(),
                    "prioridade": a.prioridade,
                    "prioridade_legivel": a.get_prioridade_display(),
                    "prioridade_ordem": _priority_order(a.prioridade),
                    "tipo": a.get_tipo_display() if a.tipo else None,
                    "sala": a.sala.numero if a.sala else None,
                    "computador": (
                        a.computador.numero_identificacao if a.computador else None
                    ),
                    "reportado_por": (
                        a.reportado_por.username if a.reportado_por else None
                    ),
                    "observacoes": a.observacoes or "",
                    "data_registo": a.data_registo.strftime("%d/%m/%Y %H:%M"),
                    "data_resolvida": (
                        a.data_resolvida.strftime("%d/%m/%Y %H:%M")
                        if a.data_resolvida
                        else None
                    ),
                    "dias_em_aberto": self._days_open(a.data_registo),
                    "esta_resolvida": a.estado == "RESOLVIDO",
                    "tem_computador": a.computador is not None,
                    "tem_observacoes": bool(a.observacoes),
                    "tem_anexos": a.anexos.exists(),
                    "numero_anexos": a.anexos.count(),
                }
            )
        return anomalias_contexto

    def _normalize_diagnosis_text(self, anomalia):
        parts = [
            anomalia.titulo or "",
            anomalia.descricao or "",
            anomalia.get_tipo_display() if anomalia.tipo else "",
        ]
        return " ".join(parts).lower()

    def _build_fallback_diagnosis(self, anomalia):
        text = self._normalize_diagnosis_text(anomalia)

        tempo = "20-40 minutos"
        causas = [
            "Ligacoes fisicas soltas ou mal encaixadas.",
            "Falha de configuracao ou de software.",
            "Componente periferico com mau funcionamento.",
        ]
        materiais = [
            "Chave Phillips",
            "Cabo de teste",
            "Computador ou periferico de teste",
        ]

        keyword_rules = [
            {
                "patterns": [r"\brede\b", r"\binternet\b", r"sem net", r"ethernet", r"wifi"],
                "tempo": "10-20 minutos",
                "causas": [
                    "Cabo de rede desligado ou danificado.",
                    "Porta de rede, switch ou ponto de acesso indisponivel.",
                    "Configuracao IP ou autenticacao de rede incorreta.",
                    "Driver de rede em falha.",
                ],
                "materiais": [
                    "Cabo Ethernet",
                    "Testador de cabos",
                    "Portatil de teste",
                    "Adaptador de rede USB",
                ],
            },
            {
                "patterns": [r"nao liga", r"não liga", r"sem energia", r"fonte", r"arranque"],
                "tempo": "15-30 minutos",
                "causas": [
                    "Fonte de alimentacao com falha.",
                    "Cabo de alimentacao ou tomada sem energia.",
                    "Botao de power ou ligacao interna com problema.",
                    "Memoria RAM mal encaixada.",
                ],
                "materiais": [
                    "Multimetro",
                    "Cabo de alimentacao de teste",
                    "Fonte de alimentacao de teste",
                    "Modulo de RAM de teste",
                ],
            },
            {
                "patterns": [r"monitor", r"sem imagem", r"ecra", r"ecrã", r"display", r"hdmi", r"vga"],
                "tempo": "10-20 minutos",
                "causas": [
                    "Cabo de video solto ou danificado.",
                    "Monitor desligado ou com entrada incorreta.",
                    "Placa grafica ou adaptador com falha.",
                    "Resolucao ou output de video incorretos.",
                ],
                "materiais": [
                    "Cabo HDMI ou VGA de teste",
                    "Monitor de teste",
                    "Adaptador de video",
                    "Portatil de teste",
                ],
            },
            {
                "patterns": [r"teclado", r"rato", r"mouse", r"usb"],
                "tempo": "10-15 minutos",
                "causas": [
                    "Porta USB sem resposta.",
                    "Periferico avariado.",
                    "Driver ou configuracao do sistema com falha.",
                    "Ligacao fisica instavel.",
                ],
                "materiais": [
                    "Teclado USB de teste",
                    "Rato USB de teste",
                    "Adaptador USB",
                    "Ar comprimido",
                ],
            },
            {
                "patterns": [r"lento", r"lentid", r"bloqueia", r"congela"],
                "tempo": "20-40 minutos",
                "causas": [
                    "Processos em excesso ou arranque sobrecarregado.",
                    "Disco com baixo desempenho ou quase cheio.",
                    "Memoria RAM insuficiente.",
                    "Atualizacoes ou software em conflito.",
                ],
                "materiais": [
                    "SSD de teste",
                    "Memoria RAM de teste",
                    "Pen USB de manutencao",
                    "Software de diagnostico",
                ],
            },
            {
                "patterns": [r"projetor", r"projetor", r"projec", r"projeç"],
                "tempo": "15-25 minutos",
                "causas": [
                    "Fonte de entrada errada no projetor.",
                    "Cabo de video ou adaptador com falha.",
                    "Lampada ou modulo de projecao com problema.",
                    "Resolucao ou duplicacao de ecran incorreta.",
                ],
                "materiais": [
                    "Cabo HDMI de teste",
                    "Adaptador de video",
                    "Portatil de teste",
                    "Comando ou pilhas de teste",
                ],
            },
        ]

        for rule in keyword_rules:
            if any(re.search(pattern, text) for pattern in rule["patterns"]):
                tempo = rule["tempo"]
                causas = rule["causas"]
                materiais = rule["materiais"]
                break

        return "\n".join(
            [
                "## Tempo estimado",
                tempo,
                "",
                "## Possiveis causas",
                *[f"- {item}" for item in causas[:4]],
                "",
                "## Materiais necessarios",
                *[f"- {item}" for item in materiais[:4]],
            ]
        )

    def build_anomaly_diagnosis_prompt(self, anomalia, anomalias):
        sala = "-"
        if anomalia.sala:
            sala = anomalia.sala.numero
        elif anomalia.computador and anomalia.computador.sala:
            sala = anomalia.computador.sala.numero

        computador = (
            anomalia.computador.numero_identificacao if anomalia.computador else "-"
        )
        tipo = anomalia.get_tipo_display() if anomalia.tipo else "-"
        historico = json.dumps(
            self._serialize_anomalias(anomalias), ensure_ascii=False, indent=2
        )

        return f"""
És o Assistente IA da plataforma Gestão de Anomalias.

Analisa esta anomalia como um técnico experiente.

Estrutura obrigatória:

## Tempo estimado
- Indica apenas um intervalo simples, por exemplo: 10–15 minutos, 15–30 minutos ou 30–60 minutos.

## Possíveis causas
- Máximo 4 itens.

## Materiais necessários
- Máximo 4 itens.
- Adapta os materiais ao tipo de anomalia e ao problema descrito.

Regras obrigatórias:
- Responde sempre em português europeu.
- Não uses saudação.
- Não escrevas introdução.
- Não escrevas conclusão.
- Não escrevas explicações extra fora destas 3 secções.
- Usa frases curtas.
- Usa no máximo 150 palavras.
- Não acrescentes secções extra.
- Não uses informação da plataforma para criar um bloco separado de ocorrências semelhantes.
- Não inventes dados.

Contexto da anomalia:
- Título: {anomalia.titulo}
- Descrição: {anomalia.descricao}
- Tipo: {tipo}
- Prioridade: {anomalia.get_prioridade_display()}
- Sala: {sala}
- Computador: {computador}
- Estado: {anomalia.get_estado_display()}

Histórico da plataforma para apoio contextual:
{historico}
"""

    def build_payload(self, pergunta, anomalias, conversation_history=None):
        conversation_context = conversation_history or []

        prompt = f"""
{self.build_system_prompt()}

{self.informacao_sistema}

Instrução adicional:
Se a pergunta for analítica e focada apenas em dados da plataforma, responde só com o resultado pedido, de forma direta, objetiva e com no máximo 2 frases.
Se a pergunta for técnica, usa exatamente a estrutura técnica obrigatória.
Se a pergunta for simples, mantém a resposta curta.
Se a pergunta for específica ou o utilizador pedir mais detalhe, podes aprofundar um pouco, sem produzir texto demasiado extenso.
Se existirem ocorrências semelhantes relevantes, apresenta-as com Sala, Computador e Estado.
Se existir informação suficiente nas observações, indica a solução mais frequente utilizada nas ocorrências semelhantes.
Se a nova pergunta for curta, ambígua ou de seguimento, usa primeiro o histórico recente da conversa para perceber a que elemento se refere.

Histórico recente da conversa:
{json.dumps(conversation_context, ensure_ascii=False, indent=2)}

Pergunta do técnico:
{pergunta}

Contexto complementar da aplicação:
A lista seguinte não substitui a tua análise técnica. Deve ser usada apenas para complementar a resposta:
{json.dumps(self._serialize_anomalias(anomalias), ensure_ascii=False, indent=2)}
"""
        return prompt

    def _call_api(self, prompt):
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    def analyze(self, pergunta, anomalias, conversation_history=None):
        prompt = self.build_payload(
            pergunta,
            anomalias,
            conversation_history=conversation_history,
        )
        resposta = self._call_api(prompt)
        return {"response": resposta}

    def diagnose_anomaly(self, anomalia, anomalias):
        prompt = self.build_anomaly_diagnosis_prompt(anomalia, anomalias)
        try:
            return self._call_api(prompt)
        except Exception:
            return self._build_fallback_diagnosis(anomalia)
