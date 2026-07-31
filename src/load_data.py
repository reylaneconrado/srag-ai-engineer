"""Carregamento e limpeza da base SRAG do Open DATASUS/SIVEP-Gripe.

Responsabilidades deste módulo
--------------------------------
1. Ler o CSV uma única vez (o orquestrador injeta o df em todas as tools).
2. Selecionar apenas as colunas necessárias ao projeto.
3. Converter datas com tolerância a erros de preenchimento.
4. Aplicar limpeza de qualidade sobre os campos usados nas métricas:
   - Remover duplicatas exatas.
   - Descartar idades biologicamente impossíveis (> 120 anos).
   - Filtrar valores fora do dicionário de domínio do DATASUS nos campos
     categóricos (EVOLUCAO, UTI, VACINA_COV).
   - Descartar registros sem data de início de sintomas (coluna âncora
     de todas as métricas temporais).

Nenhuma métrica é calculada aqui — apenas dados prontos para análise.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

ARQUIVO = "data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv"

# Colunas utilizadas no projeto (lidas na origem para economizar memória).
COLUNAS_PROJETO = [
    "DT_SIN_PRI",   # data de início de sintomas — âncora de todas as métricas
    "DT_INTERNA",   # data de internação
    "DT_EVOLUCA",   # data de evolução do caso
    "DT_DIGITA",    # data de digitação — usada para estimar imaturidade
    "SG_UF",        # UF de notificação
    "NU_IDADE_N",   # idade do paciente (anos)
    "EVOLUCAO",     # 1=cura, 2=óbito, 3=óbito por outra causa, 9=ignorado
    "UTI",          # 1=sim, 2=não, 9=ignorado
    "VACINA_COV",   # 1=sim, 2=não, 9=ignorado
]

# Valores válidos por campo, conforme dicionário de dados do DATASUS.
# Registros com valores fora desses conjuntos são tratados como ausentes
# (campo recebe NaN) para que cada métrica possa filtrar com .notna()
# sem risco de incluir códigos inválidos no denominador.
DOMINIOS_VALIDOS = {
    "EVOLUCAO":   {1, 2, 3, 9},
    "UTI":        {1, 2, 9},
    "VACINA_COV": {1, 2, 9},
}

# Nas métricas, o código 9 ("ignorado") é excluído pelo filtro .notna()
# porque a limpeza abaixo substitui 9 → NaN.  Dessa forma, mortalidade
# conta apenas EVOLUCAO ∈ {1, 2, 3}; UTI e vacinação só ∈ {1, 2}.
CODIGOS_IGNORADO = {9}

IDADE_MAX_ANOS = 120   # acima disso é erro de digitação ou unidade errada


def carregar_base(arquivo: str = ARQUIVO) -> pd.DataFrame:
    """Carrega, limpa e retorna o dataframe pronto para análise.

    Parâmetros
    ----------
    arquivo : str
        Caminho para o CSV do DATASUS (separador ";", encoding latin-1).

    Retorna
    -------
    pd.DataFrame
        Dataframe limpo com as colunas de COLUNAS_PROJETO.
        Linhas com DT_SIN_PRI ausente são removidas (campo obrigatório
        para todas as métricas temporais).
    """
    logger.info("Lendo CSV: %s", arquivo)
    df = pd.read_csv(
        arquivo,
        sep=";",
        encoding="latin1",
        low_memory=False,
        usecols=lambda c: c in COLUNAS_PROJETO,
    )
    logger.info("Linhas brutas: %d", len(df))

    # --- 1. Conversão de datas -------------------------------------------
    # O DATASUS grava as datas em formato YYYY-MM-DD (ISO), então dayfirst=False
    # é o correto — evita o UserWarning do pandas ao detectar o formato.
    for col in ("DT_SIN_PRI", "DT_INTERNA", "DT_EVOLUCA", "DT_DIGITA"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=False, errors="coerce")

    # --- 2. Remover duplicatas exatas -------------------------------------
    antes = len(df)
    df = df.drop_duplicates()
    removidas = antes - len(df)
    if removidas:
        logger.info("Duplicatas removidas: %d", removidas)

    # --- 3. Descartar registros sem data de início de sintomas -----------
    # DT_SIN_PRI é a âncora de todas as janelas temporais; sem ela o
    # registro não contribui para nenhuma métrica e só distorce contagens.
    antes = len(df)
    df = df[df["DT_SIN_PRI"].notna()]
    logger.info(
        "Registros removidos por DT_SIN_PRI ausente: %d", antes - len(df)
    )

    # --- 4. Limpeza de idade ---------------------------------------------
    # NU_IDADE_N contém a idade em anos para adultos, mas o DATASUS também
    # usa esse campo para registrar idade em dias/meses em recém-nascidos
    # com um código de unidade separado (não carregado aqui).  Valores
    # acima de IDADE_MAX_ANOS são claramente erros de digitação (ex.: 999,
    # 222) e são descartados para não distorcer análises futuras de faixa
    # etária.
    if "NU_IDADE_N" in df.columns:
        df["NU_IDADE_N"] = pd.to_numeric(df["NU_IDADE_N"], errors="coerce")
        mask_invalida = (df["NU_IDADE_N"] > IDADE_MAX_ANOS) | (df["NU_IDADE_N"] < 0)
        n_invalidas = mask_invalida.sum()
        if n_invalidas:
            logger.info(
                "Idades fora do intervalo [0, %d] substituídas por NaN: %d",
                IDADE_MAX_ANOS,
                n_invalidas,
            )
            df.loc[mask_invalida, "NU_IDADE_N"] = pd.NA

    # --- 5. Filtrar valores fora do dicionário de domínio ----------------
    for campo, validos in DOMINIOS_VALIDOS.items():
        if campo not in df.columns:
            continue
        df[campo] = pd.to_numeric(df[campo], errors="coerce")
        mask_fora = df[campo].notna() & ~df[campo].isin(validos)
        n_fora = mask_fora.sum()
        if n_fora:
            logger.info(
                "Valores fora do domínio em %s substituídos por NaN: %d",
                campo,
                n_fora,
            )
            df.loc[mask_fora, campo] = pd.NA

        # Código 9 = "ignorado" → NaN para que as métricas não o incluam
        # no denominador (ex.: UTI=9 não é "não foi para UTI").
        mask_ignorado = df[campo].isin(CODIGOS_IGNORADO)
        n_ignorado = mask_ignorado.sum()
        if n_ignorado:
            logger.info(
                "Código 'ignorado' (9) em %s substituído por NaN: %d",
                campo,
                n_ignorado,
            )
            df.loc[mask_ignorado, campo] = pd.NA

    logger.info("Linhas após limpeza: %d", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = carregar_base()
    print("\n=== Resumo pós-limpeza ===")
    print(f"Linhas:  {len(df):,}")
    print(f"Período: {df['DT_SIN_PRI'].min().date()} a {df['DT_SIN_PRI'].max().date()}")
    print("\nValores nulos por coluna:")
    print(df.isnull().sum().to_string())
    print("\nDistribuição EVOLUCAO:", df["EVOLUCAO"].value_counts(dropna=False).to_dict())
    print("Distribuição UTI:     ", df["UTI"].value_counts(dropna=False).to_dict())
    print("Distribuição VACINA:  ", df["VACINA_COV"].value_counts(dropna=False).to_dict())
