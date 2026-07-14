import pandas as pd

arquivo = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

df = pd.read_csv(
    arquivo,
    sep=";",
    encoding="latin1",
    low_memory=False
)

print("\nQuantidade de linhas e colunas:")
print(df.shape)

print("\nColunas:")
for coluna in df.columns:
    print(coluna)
    