import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="latin1",
    low_memory=False
)

# Casos com evolução conhecida
base = df[
    df["EVOLUCAO"].notna()
]

total_casos = len(base)

obitos = len(
    base[
        base["EVOLUCAO"] == 2
    ]
)

taxa_mortalidade = (
    obitos /
    total_casos
) * 100

print("\nRESULTADO")

print(
    f"Total casos avaliados: {total_casos}"
)

print(
    f"Total óbitos: {obitos}"
)

print(
    f"Taxa de mortalidade: {taxa_mortalidade:.2f}%"
)