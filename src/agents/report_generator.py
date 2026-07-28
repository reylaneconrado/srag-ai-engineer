import os
from datetime import datetime

OUTPUT_FILE = "outputs/relatorio_final.md"


def _formatar_noticias(noticias: list) -> str:
    if not noticias:
        return "_Nenhuma notícia coletada nesta execução._"

    por_categoria = {}
    for n in noticias:
        por_categoria.setdefault(n.get("categoria", "geral"), []).append(n)

    linhas = []
    for categoria, itens in por_categoria.items():
        linhas.append(f"**{categoria.replace('_', ' ').title()}**")
        for item in itens:
            link = item.get("link") or ""
            linhas.append(f"- [{item['titulo']}]({link})" if link else f"- {item['titulo']}")
        linhas.append("")
    return "\n".join(linhas)


def _correlacionar_noticias_metricas(noticias: list, metricas: dict) -> str:
    """Correlação explícita entre notícias coletadas e métricas calculadas.

    Responde ao feedback do desafio: "estabelecer uma correlação explícita
    entre cada notícia e as métricas analisadas". Gerado por código, não
    pelo LLM — o mapeamento é determinístico via categoria do RSS.
    """
    if not noticias:
        return "_Nenhuma notícia coletada nesta execução para correlacionar._"

    MAPA_CATEGORIA_METRICA = {
        "vacinacao":           ("Taxa de Vacinação",             metricas.get("vacinacao", {}).get("taxa_vacinacao_pct")),
        "geral_srag":          ("Taxa de Mortalidade / SRAG",    metricas.get("mortalidade", {}).get("taxa_mortalidade_pct")),
        "influenza":           ("Taxa de Crescimento dos Casos", metricas.get("crescimento", {}).get("taxa_crescimento_pct")),
        "virus_respiratorios": ("Taxa de Crescimento dos Casos", metricas.get("crescimento", {}).get("taxa_crescimento_pct")),
        "covid":               ("Taxa de Casos com UTI",         metricas.get("uti", {}).get("taxa_uti_pct")),
    }

    por_metrica: dict = {}
    sem_correlacao = []

    for n in noticias:
        cat = n.get("categoria", "")
        if cat in MAPA_CATEGORIA_METRICA:
            nome_metrica, valor = MAPA_CATEGORIA_METRICA[cat]
            if nome_metrica not in por_metrica:
                por_metrica[nome_metrica] = {"valor": valor, "noticias": []}
            por_metrica[nome_metrica]["noticias"].append(n)
        else:
            sem_correlacao.append(n)

    linhas = []
    for nome_metrica, info in por_metrica.items():
        valor_str = f"{info['valor']}%" if info["valor"] is not None else "N/A"
        linhas.append(f"### {nome_metrica} ({valor_str})\n")
        for n in info["noticias"]:
            link = n.get("link") or ""
            titulo = n.get("titulo", "")
            linhas.append(f"- [{titulo}]({link})" if link else f"- {titulo}")
        linhas.append("")

    if sem_correlacao:
        linhas.append("### Contexto Geral\n")
        for n in sem_correlacao:
            link = n.get("link") or ""
            titulo = n.get("titulo", "")
            linhas.append(f"- [{titulo}]({link})" if link else f"- {titulo}")

    return "\n".join(linhas)


def _montar_secao_metricas(metricas: dict) -> str:
    """Seção 2 gerada por código — nunca pelo LLM, para garantir fidelidade."""
    mortalidade = metricas.get("mortalidade", {})
    uti = metricas.get("uti", {})
    vacinacao = metricas.get("vacinacao", {})
    crescimento = metricas.get("crescimento", {})

    aviso_imaturidade = crescimento.get("aviso", "")
    nota_crescimento = f"\n\n> {aviso_imaturidade}" if aviso_imaturidade else ""

    return f"""## 2. Métricas Principais

### 2.1 Taxa de Mortalidade

**{mortalidade.get("taxa_mortalidade_pct", "N/A")}%** — {mortalidade.get("obitos", "N/A")} óbitos entre {mortalidade.get("casos_avaliados", "N/A")} casos avaliados com evolução conhecida.

### 2.2 Taxa de Casos com UTI

**{uti.get("taxa_uti_pct", "N/A")}%** — {uti.get("casos_uti", "N/A")} casos entre {uti.get("registros_com_info_uti", "N/A")} registros com essa informação preenchida. *Proxy de utilização, não representa ocupação real de leitos.*

### 2.3 Taxa de Vacinação

**{vacinacao.get("taxa_vacinacao_pct", "N/A")}%** — {vacinacao.get("vacinados", "N/A")} vacinados entre {vacinacao.get("registros_com_info_vacinacao", "N/A")} registros analisados. *Refere-se apenas aos registros desta base, não à cobertura populacional geral.*

### 2.4 Taxa de Crescimento dos Casos

**{crescimento.get("taxa_crescimento_pct", "N/A")}%** — {crescimento.get("casos_ultimos_30_dias", "N/A")} casos nos últimos 30 dias analisados vs. {crescimento.get("casos_30_dias_anteriores", "N/A")} no período de 30 dias anterior.{nota_crescimento}
"""


def montar_relatorio_final(secoes: dict, metricas: dict, validacao_guardrails: dict) -> str:
    """Monta o arquivo final combinando seção de métricas (código) e
    texto qualitativo (LLM), com correlação explícita notícia-métrica.
    """
    aviso_guardrails = ""
    if not validacao_guardrails.get("aprovado", True):
        problemas = "\n".join(f"- {p}" for p in validacao_guardrails.get("problemas", []))
        aviso_guardrails = f"""
> ⚠️ **Aviso automático de guardrails**: esta versão do texto apresentou as seguintes
> inconsistências detectadas de forma programática e deve ser revisada antes de ser
> distribuída:
{problemas}
"""

    conteudo_final = f"""# Relatório Analítico de SRAG

Data de geração: {datetime.now().strftime("%d/%m/%Y %H:%M")}
{aviso_guardrails}
---

## 1. Resumo Executivo

{secoes.get("resumo_executivo", "")}

{_montar_secao_metricas(metricas)}

## 3. Contexto Externo com Notícias

{secoes.get("contexto_noticias", "")}

### Correlação entre Notícias e Métricas

Mapeamento explícito de cada notícia coletada em tempo de execução à métrica epidemiológica correspondente:

{_correlacionar_noticias_metricas(metricas.get("noticias", []), metricas)}

## 4. Limitações da Análise

{secoes.get("limitacoes", "")}

## 5. Governança e Transparência

{secoes.get("governanca", "")}

## 6. Conclusão

{secoes.get("conclusao", "")}

---

## Dados brutos usados nesta execução (fonte da seção 2)

| Métrica | Valor |
|---|---|
| Taxa de mortalidade | {metricas.get("mortalidade", {}).get("taxa_mortalidade_pct", "N/A")}% |
| Taxa de casos com UTI (proxy) | {metricas.get("uti", {}).get("taxa_uti_pct", "N/A")}% |
| Taxa de vacinação (amostra) | {metricas.get("vacinacao", {}).get("taxa_vacinacao_pct", "N/A")}% |
| Taxa de crescimento de casos | {metricas.get("crescimento", {}).get("taxa_crescimento_pct", "N/A")}% |

## Notícias coletadas (RSS, em tempo de execução)

{_formatar_noticias(metricas.get("noticias", []))}

## Arquivos Gerados

- Gráfico diário dos últimos 30 dias: `outputs/daily_cases_30_days.png`
- Gráfico mensal dos últimos 12 meses: `outputs/monthly_cases_12_months.png`
- Log de auditoria completo desta execução: `logs/audit_log.json`

---

## Observação Técnica

Este relatório foi gerado automaticamente por um agente de Inteligência Artificial que:

- Carregou os dados estruturados do Open DATASUS/SIVEP-Gripe
- Chamou as ferramentas de cálculo de métricas e de busca de notícias em tempo de execução
- A seção "Métricas Principais" é montada diretamente a partir do retorno dessas ferramentas
  (nunca escrita pelo modelo de linguagem, para garantir 100% de fidelidade aos dados)
- A seção "Correlação entre Notícias e Métricas" mapeia cada notícia coletada à métrica
  correspondente de forma determinística por código
- Usou o modelo de linguagem executado localmente com Ollama para redigir apenas o texto
  qualitativo (resumo, contexto, limitações, governança, conclusão)
- Passou esse texto por uma validação programática de guardrails (resultado:
  {"aprovado" if validacao_guardrails.get("aprovado") else "REPROVADO — ver aviso acima"})
- Registrou cada etapa da execução no log de auditoria
"""

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(conteudo_final)

    return OUTPUT_FILE
