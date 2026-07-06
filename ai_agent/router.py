"""
Router responsável por identificar a intenção do utilizador e selecionar
a ferramenta mais adequada.

O router não utiliza IA.
A deteção é feita apenas através de palavras-chave.
"""

INTENTS = {

    "estatisticas": [
        "estatisticas",
        "estatística",
        "estatisticas gerais",
        "quantas",
        "quantos",
        "total",
        "totais",
        "número",
        "numero",
        "contagem"
    ],

    "pendentes": [
        "pendente",
        "pendentes"
    ],

    "em_resolucao": [
        "em resolução",
        "em resolucao",
        "resolver",
        "a resolver"
    ],

    "resolvidas": [
        "resolvida",
        "resolvidas",
        "concluída",
        "concluidas",
        "concluídas",
        "finalizada",
        "finalizadas"
    ],

    "resumo": [
        "resumo",
        "resumir",
        "como está",
        "como esta",
        "situação",
        "situacao",
        "estado geral",
        "esta semana",
        "hoje"
    ],

    "prioridade": [
        "prioridade",
        "prioridades",
        "urgente",
        "urgentes",
        "mais urgente",
        "resolver primeiro",
        "o que devo resolver",
        "por onde começo",
        "por onde comecar",
        "começar",
        "comecar"
    ],

    "sala": [
        "sala",
        "salas",
        "mais problemas",
        "pior sala",
        "ocorrências por sala",
        "ocorrencias por sala"
    ],

    "computador": [
        "computador",
        "computadores",
        "pc",
        "equipamento"
    ],

    "tipo": [
        "tipo",
        "tipos",
        "rede",
        "internet",
        "projetor",
        "projector",
        "limpeza",
        "limpeza",
        "mobiliário",
        "mobiliario",
        "acesso"
    ],

    "utilizador": [
        "reportou",
        "reportado",
        "utilizador",
        "professor"
    ],

    "data": [
        "ontem",
        "hoje",
        "esta semana",
        "este mês",
        "este mes",
        "últimos dias",
        "ultimos dias",
        "últimas",
        "ultimas"
    ],

    "ajuda": [
        "ajuda",
        "como usar",
        "como funciona",
        "explica",
        "manual",
        "o que podes fazer",
        "o que consegues fazer"
    ]
}


def detect_tool(question: str) -> str | None:
    """
    Analisa a pergunta do utilizador e devolve a intenção
    correspondente.

    Returns:
        Nome da ferramenta ou None caso não exista correspondência.
    """

    if not question:
        return None

    text = question.lower().strip()

    for tool, keywords in INTENTS.items():

        for keyword in keywords:

            if keyword in text:
                return tool

    return None