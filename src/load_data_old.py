import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

COLUNAS_PROJETO = [
    "DT_SIN_PRI",
    "DT_INTERNA",
    "DT_EVOLUCA",
    "DT_DIGITA",
    "SG_UF",
    "NU_IDADE_N",
    "EVOLUCAO",
    "UTI",
    "VACINA_COV",
]


def carregar_base(arquivo: str = ARQUIVO) -> pd.DataFrame:
    """Carrega e limpa a base uma única vez.

    Antes, cada script (mortality.py, uti.py, vaccination.py,
    growth_rate.py, os geradores de gráfico...) lia o CSV de 160MB+
    de forma independente. Isso é lento e, mais importante, impede
    que o agente reutilize o mesmo dataframe entre chamadas de tools.
    Agora o orquestrador carrega uma vez e passa o df para cada tool.
    """
    df = pd.read_csv(
        arquivo,
        sep=";",
        encoding="latin1",
        low_memory=False,
        usecols=lambda c: c in COLUNAS_PROJETO,
    )

    for col in ("DT_SIN_PRI", "DT_INTERNA", "DT_EVOLUCA", "DT_DIGITA"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


if __name__ == "__main__":
    df = carregar_base()
    print("Linhas:", len(df))
    print("Colunas:", list(df.columns))
    print("Período de sintomas:", df["DT_SIN_PRI"].min(), "a", df["DT_SIN_PRI"].max())
