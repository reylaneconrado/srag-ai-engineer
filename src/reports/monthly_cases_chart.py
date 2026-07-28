import os
import pandas as pd
import matplotlib.pyplot as plt


def gerar_grafico_mensal(df: pd.DataFrame, saida: str = "outputs/monthly_cases_12_months.png") -> str:
    df = df.copy()
    df["MES"] = df["DT_SIN_PRI"].dt.to_period("M")

    serie = df.groupby("MES").size().tail(12)

    plt.figure(figsize=(12, 5))
    plt.plot(serie.index.astype(str), serie.values, marker="o")
    plt.title("Casos Mensais SRAG - Últimos 12 Meses")
    plt.xlabel("Mês")
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

    caminho = gerar_grafico_mensal(carregar_base())
    print(f"Gráfico salvo em {caminho}")
