import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="latin1",
    low_memory=False
)

# Registros com informação de UTI
base = df[df["UTI"].notna()]

total_casos = len(base)

casos_uti = len(
    base[
        base["UTI"] == 1
    ]
)

taxa_uti = (
    casos_uti /
    total_casos
) * 100

print("\nRESULTADO")

print(
    f"Total casos analisados: {total_casos}"
)

print(
    f"Casos com UTI: {casos_uti}"
)

print(
    f"Taxa UTI: {taxa_uti:.2f}%"
)