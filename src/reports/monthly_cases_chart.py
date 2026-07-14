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

# Agrupamento por mês
df["MES"] = df["DT_SIN_PRI"].dt.to_period("M")

serie = (
    df.groupby("MES")
      .size()
      .tail(12)
)

plt.figure(figsize=(12,5))

plt.plot(
    serie.index.astype(str),
    serie.values,
    marker="o"
)

plt.title(
    "Casos Mensais SRAG - Últimos 12 Meses"
)

plt.xlabel("Mês")

plt.ylabel("Quantidade de Casos")

plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(
    "outputs/monthly_cases_12_months.png"
)

print(
    "\nGráfico salvo em outputs/monthly_cases_12_months.png"
)