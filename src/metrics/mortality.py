import pandas as pd


def calcular_mortalidade(df: pd.DataFrame) -> dict:
    """Calcula a taxa de mortalidade entre os casos com evolução conhecida.

    Retorna um dicionário (não imprime nada) para poder ser usado
    como resultado de uma tool chamada pelo agente.
    """
    base = df[df["EVOLUCAO"].notna()]

    total_casos = len(base)
    obitos = len(base[base["EVOLUCAO"] == 2])

    taxa = (obitos / total_casos) * 100 if total_casos else 0.0

    return {
        "taxa_mortalidade_pct": round(taxa, 2),
        "casos_avaliados": int(total_casos),
        "obitos": int(obitos),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from load_data import carregar_base

    df = carregar_base()
    print(calcular_mortalidade(df))
