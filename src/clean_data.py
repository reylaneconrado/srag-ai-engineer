import pandas as pd

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

print("Carregando base...")

df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="latin1",
    low_memory=False
)

# Colunas que vamos usar
colunas = [
    "DT_SIN_PRI",
    "DT_INTERNA",
    "DT_EVOLUCA",
    "SG_UF",
    "NU_IDADE_N",
    "EVOLUCAO",
    "UTI",
    "VACINA_COV"
]

df = df[colunas].copy()

print("\nConvertendo datas...")

df["DT_SIN_PRI"] = pd.to_datetime(
    df["DT_SIN_PRI"],
    errors="coerce"
)

df["DT_INTERNA"] = pd.to_datetime(
    df["DT_INTERNA"],
    errors="coerce"
)

df["DT_EVOLUCA"] = pd.to_datetime(
    df["DT_EVOLUCA"],
    errors="coerce"
)

print("\nResumo da base:")

print(df.info())

print("\nPrimeiras linhas:")

print(df.head())

print("\nValores nulos:")

print(df.isnull().sum())