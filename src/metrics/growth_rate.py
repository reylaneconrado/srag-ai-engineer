import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="latin1",
    low_memory=False
)

df["DT_SIN_PRI"] = pd.to_datetime(
    df["DT_SIN_PRI"],
    errors="coerce"
)

data_max = df["DT_SIN_PRI"].max()

inicio_atual = data_max - pd.Timedelta(days=29)
inicio_anterior = data_max - pd.Timedelta(days=59)
fim_anterior = data_max - pd.Timedelta(days=30)

periodo_atual = df[
    (df["DT_SIN_PRI"] >= inicio_atual)
]

periodo_anterior = df[
    (df["DT_SIN_PRI"] >= inicio_anterior)
    &
    (df["DT_SIN_PRI"] <= fim_anterior)
]

casos_atual = len(periodo_atual)

casos_anterior = len(periodo_anterior)

taxa = (
    (casos_atual - casos_anterior)
    / casos_anterior
) * 100

print("\nRESULTADO")

print(f"Casos últimos 30 dias: {casos_atual}")

print(f"Casos 30 dias anteriores: {casos_anterior}")

print(f"Taxa de crescimento: {taxa:.2f}%")