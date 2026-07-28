import pandas as pd

# Atraso mediano observado entre data de início de sintomas (DT_SIN_PRI)
# e data de digitação (DT_DIGITA) na base é de ~7 dias. Isso significa que
# os últimos dias da base SEMPRE aparentam ter menos casos do que
# realmente vão ter quando a notificação for concluída — não porque os
# casos caíram, mas porque ainda não foram todos digitados no sistema.
#
# Bug identificado na versão anterior: o cálculo comparava os "últimos 30
# dias" usando a última data do arquivo como âncora, incluindo esse
# período ainda incompleto. Isso gerava uma taxa de crescimento fortemente
# negativa (queda "fake" de casos) mesmo quando a tendência real era de
# alta (ex: maio/2025 teve quase o dobro de casos de junho/2025 só porque
# junho estava com a base parcial).
#
# Correção: a data-âncora da janela "atual" é deslocada para trás em
# JANELA_IMATURIDADE_DIAS antes de calcular qualquer coisa.
JANELA_IMATURIDADE_DIAS = 10


def calcular_crescimento(df: pd.DataFrame, janela_imaturidade_dias: int = JANELA_IMATURIDADE_DIAS) -> dict:
    data_max_bruta = df["DT_SIN_PRI"].max()

    # Data-âncora "madura": ignora os últimos N dias, que ainda estão
    # sujeitos a atraso de notificação.
    ancora = data_max_bruta - pd.Timedelta(days=janela_imaturidade_dias)

    inicio_atual = ancora - pd.Timedelta(days=29)
    inicio_anterior = ancora - pd.Timedelta(days=59)
    fim_anterior = ancora - pd.Timedelta(days=30)

    periodo_atual = df[(df["DT_SIN_PRI"] >= inicio_atual) & (df["DT_SIN_PRI"] <= ancora)]
    periodo_anterior = df[(df["DT_SIN_PRI"] >= inicio_anterior) & (df["DT_SIN_PRI"] <= fim_anterior)]

    casos_atual = len(periodo_atual)
    casos_anterior = len(periodo_anterior)

    taxa = ((casos_atual - casos_anterior) / casos_anterior) * 100 if casos_anterior else 0.0

    return {
        "taxa_crescimento_pct": round(taxa, 2),
        "casos_ultimos_30_dias": int(casos_atual),
        "casos_30_dias_anteriores": int(casos_anterior),
        "data_max_bruta_arquivo": str(data_max_bruta.date()),
        "data_ancora_usada": str(ancora.date()),
        "dias_finais_excluidos_por_imaturidade": janela_imaturidade_dias,
        "aviso": (
            f"Os últimos {janela_imaturidade_dias} dias de sintomas da base "
            "(até "
            f"{data_max_bruta.date()}) foram excluídos do cálculo porque a "
            "notificação de casos recentes ainda está incompleta (atraso "
            "mediano de digitação de ~7 dias). Incluí-los sub-estima "
            "artificialmente os casos recentes e pode inverter o sinal da "
            "taxa de crescimento."
        ),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from load_data import carregar_base

    df = carregar_base()
    print(calcular_crescimento(df))
