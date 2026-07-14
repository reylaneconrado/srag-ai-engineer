import pandas as pd
import matplotlib.pyplot as plt

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

inicio = data_max - pd.Timedelta(days=29)

df_30 = df[
    df["DT_SIN_PRI"] >= inicio
]

serie = (
    df_30
    .groupby("DT_SIN_PRI")
    .size()
)

plt.figure(figsize=(12,5))

plt.plot(
    serie.index,
    serie.values,
    marker="o"
)

plt.title(
    "Casos Diários SRAG - Últimos 30 Dias"
)

plt.xlabel("Data")

plt.ylabel("Quantidade de Casos")

plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(
    "outputs/daily_cases_30_days.png"
)

print(
    "\nGráfico salvo em outputs/daily_cases_30_days.png"
)