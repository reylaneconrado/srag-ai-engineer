"""Define as ferramentas (tools) que o agente pode chamar e um dispatcher
que as executa de fato, registrando cada chamada na auditoria.

Isso é o que faltava no projeto original: o `orchestrator.py` não
executava nenhuma lógica, e o `report_generator.py` não chamava nenhuma
dessas funções — os valores estavam hardcoded no prompt.
"""

from metrics.mortality import calcular_mortalidade
from metrics.uti import calcular_uti
from metrics.vaccination import calcular_vacinacao
from metrics.growth_rate import calcular_crescimento
from news.news_collector import buscar_noticias
from utils.audit import registrar_log

# Schema no formato aceito pela API de tool-calling do Ollama
# (compatível com o formato usado por OpenAI function calling).
# Use um modelo com suporte a tools no Ollama (ex.: llama3.1, qwen2.5,
# mistral-nemo). O llama3 (3.0) original não segue bem esse contrato.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calcular_mortalidade",
            "description": "Calcula a taxa de mortalidade (óbitos / casos com evolução conhecida) na base SRAG.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_uti",
            "description": "Calcula a taxa de casos SRAG que passaram por UTI (proxy, não ocupação real de leitos).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_vacinacao",
            "description": "Calcula a taxa de vacinação entre os registros que informaram essa variável.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_crescimento",
            "description": "Calcula a taxa de crescimento de casos comparando os últimos 30 dias com os 30 dias anteriores, excluindo o período final ainda imaturo por atraso de notificação.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_noticias",
            "description": "Busca notícias atuais via RSS sobre SRAG, influenza, covid e vacinação no Brasil.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def montar_dispatcher(df):
    """Retorna {nome_da_tool: callable} vinculado ao dataframe já carregado.

    O df é carregado uma única vez pelo orquestrador e injetado aqui —
    as tools não recarregam o CSV a cada chamada.
    """

    def _run(nome, func, *args):
        resultado = func(*args)
        registrar_log(acao=f"tool_call:{nome}", valor=resultado)
        return resultado

    return {
        "calcular_mortalidade": lambda: _run("calcular_mortalidade", calcular_mortalidade, df),
        "calcular_uti": lambda: _run("calcular_uti", calcular_uti, df),
        "calcular_vacinacao": lambda: _run("calcular_vacinacao", calcular_vacinacao, df),
        "calcular_crescimento": lambda: _run("calcular_crescimento", calcular_crescimento, df),
        "buscar_noticias": lambda: _run("buscar_noticias", buscar_noticias),
    }
