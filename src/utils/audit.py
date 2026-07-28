import json
import os
from datetime import datetime

LOG_PATH = "logs/audit_log.json"


def registrar_log(acao: str, valor) -> None:
    """Acrescenta um registro de auditoria.

    O ponto central da correção: esta função agora é chamada pelo
    orquestrador em CADA etapa do fluxo (carregar dados, cada tool
    executada, prompt enviado ao LLM, resposta recebida, resultado da
    validação de guardrails), e não apenas definida e esquecida.
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    registro = {
        "data_execucao": datetime.now().isoformat(),
        "acao": acao,
        "valor": valor,
    }

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        dados = []

    dados.append(registro)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False, default=str)
