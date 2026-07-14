import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="latin1",
    low_memory=False
)

base = df[df["VACINA_COV"].notna()]

total = len(base)

vacinados = len(
    base[
        base["VACINA_COV"] == 1
    ]
)

taxa = (
    vacinados /
    total
) * 100

print("\nRESULTADO")

print(f"Total registros: {total}")

print(f"Vacinados: {vacinados}")

print(f"Taxa de vacinação: {taxa:.2f}%")
