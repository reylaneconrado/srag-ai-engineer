"""Guardrails programáticos.

O feedback do desafio apontou que os guardrails estavam concentrados
apenas no texto do prompt (ex: "a taxa de crescimento negativa significa
redução de casos"), sem nenhuma validação de código — e que uma dessas
instruções fixas reforçou uma conclusão incorreta.

Este módulo substitui/complementa isso por verificações programáticas
que rodam DEPOIS que o LLM gera o texto, e podem barrar ou sinalizar
o relatório antes de ele ser salvo.
"""

import re

TERMOS_PROIBIDOS = [
    # Antes: r"diagn[oó]stico" sozinho pegava até uso legítimo do termo em
    # contexto epidemiológico (ex.: "metodologias de diagnóstico e reporte"
    # falando de como os casos são confirmados). Agora só pega quando é
    # claramente uma AÇÃO de diagnosticar/recomendar (o que a regra
    # realmente quer evitar: o agente diagnosticando um paciente).
    r"(realizar|fazer|fornecer|dar)\s+(um\s+|o\s+)?diagn[oó]stico",
    r"diagn[oó]stico\s+m[ée]dico\b",
    r"tratamento cl[ií]nico",
    r"recomend[ao] (o|a) uso de",
    r"crise econ[oô]mica",
    r"or[cç]amento",
    r"impacto financeiro",
    r"custos? p[uú]blicos?",
    r"custos? privados?",
    r"custo[- ]benef[ií]cio",
]

# Padrões que indicam que o modelo escreveu um PLACEHOLDER em vez de
# substituir pelo valor real (ex.: "**X%**", "onde Y é o valor percentual").
# Isso aconteceu na prática: o llama3.1 chamou todas as tools corretamente,
# mas na hora de escrever o texto final "esqueceu" os números e escreveu
# letras no lugar.
PADROES_PLACEHOLDER = [
    r"\*\*[A-Z]%\*\*",
    r"\bonde [A-Z] é o valor\b",
    r"\[?(valor|percentual|número)_?(aqui|placeholder|exemplo)\]?",
]


def _tem_algum(texto: str, opcoes: list[str]) -> bool:
    texto_low = texto.lower()
    return any(opcao.lower() in texto_low for opcao in opcoes)


# Palavras que, se aparecerem na mesma FRASE antes do termo proibido,
# indicam que a frase está NEGANDO aquilo (ex: "não pretende realizar
# diagnóstico médico nem recomendar tratamento clínico"), e portanto não
# deve ser tratada como violação.
_PADRAO_NEGACAO = re.compile(r"\bn[ãa]o\b|\bsem\b|\bnenhum\w*\b|\bnunca\b", re.IGNORECASE)
_QUEBRA_DE_FRASE = re.compile(r"[.!?\n]")


def _termo_proibido_sem_negacao(texto: str, termo: str) -> bool:
    for m in re.finditer(termo, texto, flags=re.IGNORECASE):
        # Início da frase atual: última quebra de frase antes do termo.
        quebras_antes = list(_QUEBRA_DE_FRASE.finditer(texto, 0, m.start()))
        inicio_frase = quebras_antes[-1].end() if quebras_antes else 0
        frase_antes_do_termo = texto[inicio_frase:m.start()]

        if _PADRAO_NEGACAO.search(frase_antes_do_termo):
            continue  # está negado dentro da mesma frase -> ok
        return True
    return False


# Tools que TÊM que ter sido chamadas para o relatório ser confiável.
# Se alguma estiver ausente do dict de métricas, o texto pode conter
# números/períodos inventados pelo modelo em vez de dados reais.
TOOLS_OBRIGATORIAS = {
    "mortalidade": "calcular_mortalidade",
    "uti": "calcular_uti",
    "vacinacao": "calcular_vacinacao",
    "crescimento": "calcular_crescimento",
}


def validar_relatorio(texto: str, metricas: dict, texto_noticias: str = "") -> dict:
    """Roda uma série de checagens objetivas sobre o texto gerado pelo LLM.

    `texto_noticias`, se informado, é o conteúdo da seção "Contexto Externo
    com Notícias" (secoes["contexto_noticias"]). É esperado que essa seção
    cite termos como "SARS-CoV-2", "influenza por região" etc. ao resumir
    manchetes reais — isso não é dado inventado pelo modelo, é o conteúdo
    da notícia. Por isso a checagem de tópicos fora de escopo (item 6)
    ignora esse trecho; as demais checagens continuam rodando sobre o
    texto completo.

    Retorna um dict com `aprovado: bool` e a lista de problemas
    encontrados. O orquestrador decide o que fazer com isso (bloquear,
    reenviar ao LLM pedindo correção, ou apenas anexar um aviso).
    """
    problemas = []

    # 0. Alguma tool obrigatória não foi chamada? Se sim, qualquer número
    #    dessa métrica que apareça no texto é suspeito de ser inventado.
    for chave, nome_tool in TOOLS_OBRIGATORIAS.items():
        if not metricas.get(chave):
            problemas.append(
                f"A tool '{nome_tool}' não retornou dados (não foi chamada ou falhou). "
                "Qualquer valor dessa métrica mencionado no texto deve ser tratado como "
                "não confiável/possivelmente inventado pelo modelo."
            )

    # 1. Termos proibidos / extrapolações não sustentadas pelos dados
    #    (ignora ocorrências claramente negadas, ex: "não recomenda tratamento clínico")
    for termo in TERMOS_PROIBIDOS:
        if _termo_proibido_sem_negacao(texto, termo):
            problemas.append(f"Termo potencialmente indevido encontrado no texto: '{termo}'")

    # 2. A direção da taxa de crescimento no TEXTO precisa bater com o
    #    SINAL calculado. Isso é o que teria pego o bug original.
    taxa = metricas.get("crescimento", {}).get("taxa_crescimento_pct")
    if taxa is not None:
        direcao_real = "alta" if taxa > 0 else "queda" if taxa < 0 else "estabilidade"
        menciona_alta = bool(re.search(r"\baumento\b|\balta\b|\bcrescimento\b|\bsubiu\b", texto, re.IGNORECASE))
        menciona_queda = bool(re.search(r"\bqueda\b|\breduc\w*\b|\bdiminui\w*\b|\bcaiu\b", texto, re.IGNORECASE))

        if direcao_real == "alta" and menciona_queda and not menciona_alta:
            problemas.append(
                f"Inconsistência: taxa de crescimento calculada é positiva (+{taxa}%), "
                "mas o texto menciona queda/redução de casos."
            )
        if direcao_real == "queda" and menciona_alta and not menciona_queda:
            problemas.append(
                f"Inconsistência: taxa de crescimento calculada é negativa ({taxa}%), "
                "mas o texto menciona aumento/alta de casos."
            )

    # 3. Consistência NUMÉRICA: para cada métrica, qualquer percentual
    #    mencionado perto da palavra-chave correspondente ("mortalidade",
    #    "UTI", "vacina...", "crescimento") precisa bater com o valor real
    #    retornado pela tool. Isso pega o caso em que o modelo chama a tool
    #    certa mas escreve um número diferente na hora de redigir o texto
    #    (ex.: real 13,75% de crescimento, texto diz "0,54%").
    CAMPOS_TAXA = {
        "mortalidade": ("taxa_mortalidade_pct", r"mortalidade"),
        "uti": ("taxa_uti_pct", r"\bUTI\b"),
        "vacinacao": ("taxa_vacinacao_pct", r"vacina\w*"),
        "crescimento": ("taxa_crescimento_pct", r"crescimento"),
    }

    for chave, (campo, palavra) in CAMPOS_TAXA.items():
        valor_real = metricas.get(chave, {}).get(campo)
        if valor_real is None:
            continue

        percentuais_proximos = []
        for m in re.finditer(palavra, texto, re.IGNORECASE):
            # Usa o PARÁGRAFO/bloco (delimitado por linha em branco) em vez de
            # uma janela fixa de caracteres — uma janela fixa "vazava" para a
            # seção vizinha em relatórios com seções curtas (ex.: pegou o
            # percentual de vacinação ao checar a palavra "crescimento" só
            # porque as duas seções ficavam a poucos caracteres de distância).
            inicio_bloco = texto.rfind("\n\n", 0, m.start())
            inicio_bloco = 0 if inicio_bloco == -1 else inicio_bloco + 2
            fim_bloco = texto.find("\n\n", m.end())
            fim_bloco = len(texto) if fim_bloco == -1 else fim_bloco
            bloco = texto[inicio_bloco:fim_bloco]

            percentuais_proximos.extend(
                float(n.replace(",", ".")) for n in re.findall(r"(-?\d+(?:[.,]\d+)?)\s*%", bloco)
            )

        if not percentuais_proximos:
            # Nota: com o novo desenho, os números das 4 métricas centrais
            # são sempre inseridos por código na seção 2 do relatório (ver
            # report_generator.py) — o LLM escreve só o texto qualitativo
            # (resumo, contexto, limitações, conclusão) e é INSTRUÍDO a não
            # repetir os percentuais exatos nessas seções. Por isso, não
            # exigimos mais que a palavra-chave apareça com um número perto:
            # isso passou a ser esperado e correto. Se o modelo mencionar um
            # número de qualquer forma, ainda checamos consistência abaixo.
            continue

        mais_proximo = min(percentuais_proximos, key=lambda v: abs(v - valor_real))
        tolerancia = max(1.0, abs(valor_real) * 0.15)  # 1 ponto percentual ou 15%, o que for maior
        if abs(mais_proximo - valor_real) > tolerancia:
            problemas.append(
                f"Inconsistência numérica na métrica '{chave}': o texto menciona {mais_proximo}% "
                f"perto da palavra '{palavra}', mas o valor real calculado pela tool é {valor_real}%."
            )

    # 4. Placeholders não substituídos (ex.: "**X%**" em vez do valor real).
    #    O modelo chamou a tool corretamente mas "esqueceu" o número na hora
    #    de escrever — isso é diferente de inventar um número errado, e
    #    merece uma checagem própria.
    for padrao in PADROES_PLACEHOLDER:
        if re.search(padrao, texto):
            problemas.append(
                f"O texto contém um placeholder não substituído por um valor real "
                f"(padrão detectado: '{padrao}'). O modelo aparentemente chamou as "
                "tools mas não usou os números retornados ao escrever o relatório."
            )

    # 5. "Mundo fechado": as únicas 4 métricas que este agente sabe calcular
    #    são mortalidade, UTI, vacinação e crescimento. Qualquer percentual
    #    no texto que não corresponda (dentro da tolerância) a NENHUMA
    #    dessas é suspeito de ter sido inventado pelo modelo — foi o que
    #    aconteceu na prática quando o Qwen inventou "distribuição de óbitos
    #    por estado", "taxa de casos por região" e "confirmação por
    #    SARS-CoV-2 (53%)", que não vêm de nenhuma tool deste projeto.
    valores_conhecidos = [
        v for v in (
            metricas.get("mortalidade", {}).get("taxa_mortalidade_pct"),
            metricas.get("uti", {}).get("taxa_uti_pct"),
            metricas.get("vacinacao", {}).get("taxa_vacinacao_pct"),
            metricas.get("crescimento", {}).get("taxa_crescimento_pct"),
        )
        if v is not None
    ]

    if valores_conhecidos:
        percentuais_no_texto = {
            float(n.replace(",", ".")) for n in re.findall(r"(-?\d+(?:[.,]\d+)?)\s*%", texto)
        }
        for p in sorted(percentuais_no_texto):
            bate_com_algum = any(abs(p - v) <= max(1.0, abs(v) * 0.15) for v in valores_conhecidos)
            if not bate_com_algum:
                problemas.append(
                    f"O texto menciona {p}%, que não corresponde a nenhuma das 4 métricas "
                    "realmente calculadas pelas tools (mortalidade, UTI, vacinação, crescimento). "
                    "Isso é um forte indício de dado inventado pelo modelo — este agente não tem "
                    "nenhuma tool que calcule taxas por estado, região, comorbidade ou outras "
                    "quebras demográficas."
                )

    # 5b. Mesma ideia do item 5, mas para CONTAGENS ABSOLUTAS (óbitos, total
    #     de casos, registros com UTI/vacinação etc.), não só percentuais.
    #     Isso pega o caso em que o modelo acerta um percentual "próximo o
    #     suficiente" (ex.: 7,45% vs real 7,73%, dentro da tolerância) mas
    #     inventa contagens completamente diferentes (ex.: "3.064 óbitos de
    #     41.296 casos" quando o real é "9.885 óbitos de 127.927 casos").
    contagens_conhecidas = [
        v for v in (
            metricas.get("mortalidade", {}).get("obitos"),
            metricas.get("mortalidade", {}).get("casos_avaliados"),
            metricas.get("uti", {}).get("casos_uti"),
            metricas.get("uti", {}).get("registros_com_info_uti"),
            metricas.get("vacinacao", {}).get("vacinados"),
            metricas.get("vacinacao", {}).get("registros_com_info_vacinacao"),
            metricas.get("crescimento", {}).get("casos_ultimos_30_dias"),
            metricas.get("crescimento", {}).get("casos_30_dias_anteriores"),
        )
        if v is not None
    ]

    if contagens_conhecidas:
        # Números com separador de milhar (1.234 / 1,234) ou com 4+ dígitos
        # corridos, desde que não estejam colados a um "%" (isso já é
        # tratado nas checagens de percentual acima).
        padrao_contagem = re.compile(r"\b(\d{1,3}(?:[.,]\d{3})+|\d{4,})\b(?!\s*%)")
        contagens_no_texto = set()
        for m in padrao_contagem.finditer(texto):
            valor = int(re.sub(r"[.,]", "", m.group(1)))
            if 1900 <= valor <= 2100:
                continue  # provavelmente um ano, não uma contagem
            contagens_no_texto.add(valor)

        for c in sorted(contagens_no_texto):
            bate_com_alguma = any(abs(c - v) <= max(5, v * 0.02) for v in contagens_conhecidas)
            if not bate_com_alguma:
                problemas.append(
                    f"O texto menciona a contagem {c}, que não corresponde a nenhum dos números "
                    "absolutos reais retornados pelas tools (óbitos, casos avaliados, casos UTI, "
                    "registros de vacinação etc.). Forte indício de dado inventado pelo modelo."
                )


    # 6. Tópicos fora do escopo das tools disponíveis. Mesmo sem número
    #    percentual junto, mencionar essas categorias já é sinal de invenção,
    #    porque nenhuma tool deste projeto produz esse tipo de dado.
    #    Exceção: se a frase está NEGANDO/descartando o tópico (ex.: "os
    #    dados não permitem análise por estado ou comorbidades"), isso é uma
    #    limitação sendo declarada corretamente, não uma invenção — usa a
    #    mesma checagem de negação por frase dos termos proibidos.
    TOPICOS_FORA_DE_ESCOPO = [
        r"por estado\b",
        r"por regi[aã]o\b",
        r"comorbidades?\b",
        r"sars-cov-2",
    ]
    # Remove a seção de notícias antes de checar: citar esses termos ao
    # resumir uma manchete real (ex.: título de uma notícia sobre SARS-CoV-2)
    # não é o modelo inventando um dado, é reportar o conteúdo da fonte.
    texto_para_topicos = texto.replace(texto_noticias, "") if texto_noticias else texto
    for topico in TOPICOS_FORA_DE_ESCOPO:
        if _termo_proibido_sem_negacao(texto_para_topicos, topico):
            problemas.append(
                f"O texto menciona '{topico}', uma categoria de dado que nenhuma tool deste "
                "projeto calcula. Provavelmente é informação inventada pelo modelo."
            )

    # Observação: os disclaimers de UTI ser proxy, vacinação ser amostra, e a
    # nota de imaturidade de dados NÃO dependem mais do texto do LLM — o
    # `report_generator` os inclui de forma garantida e determinística no
    # documento final, então não precisam ser checados aqui.

    return {
        "aprovado": len(problemas) == 0,
        "problemas": problemas,
    }
