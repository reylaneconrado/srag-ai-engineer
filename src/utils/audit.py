import json
from datetime import datetime

def registrar_log(acao, valor):

    registro = {
        "data_execucao": datetime.now().isoformat(),
        "acao": acao,
        "valor": valor
    }

    try:
        with open(
            "logs/audit_log.json",
            "r",
            encoding="utf-8"
        ) as f:
            dados = json.load(f)

    except:
        dados = []

    dados.append(registro)

    with open(
        "logs/audit_log.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            dados,
            f,
            indent=4,
            ensure_ascii=False
        )