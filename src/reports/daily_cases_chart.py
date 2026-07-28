import os
import pandas as pd
import matplotlib.pyplot as plt


def gerar_grafico_diario(df: pd.DataFrame, saida: str = "outputs/daily_cases_30_days.png") -> str:
    data_max = df["DT_SIN_PRI"].max()
    inicio = data_max - pd.Timedelta(days=29)

    df_30 = df[df["DT_SIN_PRI"] >= inicio]
    serie = df_30.groupby("DT_SIN_PRI").size()

    plt.figure(figsize=(12, 5))
    plt.plot(serie.index, serie.values, marker="o")
    plt.title("Casos Diários SRAG - Últimos 30 Dias (dados de sintomas)")
    plt.xlabel("Data")
    plt.ylabel("Quantidade de Casos")
    plt.xticks(rotation=45)
    plt.tight_layout()

    os.makedirs(os.path.dirname(saida), exist_ok=True)
    plt.savefig(saida)
    plt.close()

    return saida


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from load_data import carregar_base

    caminho = gerar_grafico_diario(carregar_base())
    print(f"Gráfico salvo em {caminho}")
