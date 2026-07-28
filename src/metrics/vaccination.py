import pandas as pd


def calcular_vacinacao(df: pd.DataFrame) -> dict:
    """Taxa de vacinação entre os registros analisados que informaram
    VACINA_COV. NÃO representa cobertura vacinal da população geral.
    """
    base = df[df["VACINA_COV"].notna()]

    total = len(base)
    vacinados = len(base[base["VACINA_COV"] == 1])

    taxa = (vacinados / total) * 100 if total else 0.0

    return {
        "taxa_vacinacao_pct": round(taxa, 2),
        "vacinados": int(vacinados),
        "registros_com_info_vacinacao": int(total),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from load_data import carregar_base

    df = carregar_base()
    print(calcular_vacinacao(df))
