import pandas as pd


def calcular_uti(df: pd.DataFrame) -> dict:
    """Proxy de utilização de UTI entre os casos SRAG com essa informação
    preenchida. NÃO representa ocupação real de leitos de UTI no país.
    """
    base = df[df["UTI"].notna()]

    total = len(base)
    casos_uti = len(base[base["UTI"] == 1])

    taxa = (casos_uti / total) * 100 if total else 0.0

    return {
        "taxa_uti_pct": round(taxa, 2),
        "casos_uti": int(casos_uti),
        "registros_com_info_uti": int(total),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from load_data import carregar_base

    df = carregar_base()
    print(calcular_uti(df))
