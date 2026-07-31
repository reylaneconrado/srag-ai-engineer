# SRAG AI Engineer — Indicium HealthCare PoC

Prova de Conceito desenvolvida para a **Indicium HealthCare Inc.**: um agente de IA que consulta dados reais do Open DATASUS/SIVEP-Gripe, coleta notícias em tempo real e gera um relatório epidemiológico automatizado sobre a Síndrome Respiratória Aguda Grave (SRAG).

---

## Sumário

- [Contexto](#contexto)
- [Arquitetura](#arquitetura)
- [Fluxo de Execução](#fluxo-de-execução)
- [Métricas Calculadas](#métricas-calculadas)
- [Guardrails e Governança](#guardrails-e-governança)
- [Estrutura do Repositório](#estrutura-do-repositório)
- [Pré-requisitos e Instalação](#pré-requisitos-e-instalação)
- [Como Executar](#como-executar)
- [Dados](#dados)
- [Saídas](#saídas)
- [Limitações Conhecidas](#limitações-conhecidas)

---

## Contexto

A solução responde à necessidade de profissionais de saúde terem acesso a indicadores epidemiológicos atualizados sobre SRAG. Utiliza o conjunto de dados público do Open DATASUS (versão 26/06/2025, ~165.000 internações) e fontes de notícias via RSS para contextualizar as métricas com informações do momento da execução.

---

## Arquitetura

O diagrama conceitual completo está em [`architecture_diagram.pdf`](./architecture_diagram.pdf).

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENTE ORQUESTRADOR                        │
│                  (orchestrator.py)                           │
│                                                              │
│  1. Carrega o dataframe (load_data.py) — uma única vez       │
│  2. Chama as 5 tools por código (execução determinística)    │
│  3. Envia dados reais ao LLM — só para texto qualitativo     │
│  4. Valida o texto via guardrails programáticos              │
│  5. Reitera (até 2x) se reprovado                            │
│  6. Monta e salva o relatório final                          │
└────────────────────────┬────────────────────────────────────┘
                         │ injeta df
          ┌──────────────▼──────────────────────────────┐
          │              TOOLS (tools.py)                │
          │  Dispatcher que executa e loga cada chamada  │
          │                                              │
          │  calcular_mortalidade(df)                    │
          │  calcular_uti(df)                            │
          │  calcular_vacinacao(df)                      │
          │  calcular_crescimento(df)                    │
          │  buscar_noticias()  ←── RSS (Google News)    │
          └──────────────┬──────────────────────────────┘
                         │ resultados reais
          ┌──────────────▼──────────────────────────────┐
          │         LLM LOCAL (Ollama / qwen2.5:7b)      │
          │  Escreve APENAS o texto qualitativo          │
          │  em JSON estruturado — nunca os números      │
          └──────────────┬──────────────────────────────┘
                         │ JSON com 5 seções
          ┌──────────────▼──────────────────────────────┐
          │          GUARDRAILS (guardrails.py)          │
          │  Validação programática do texto gerado      │
          └──────────────┬──────────────────────────────┘
                         │ aprovado / problemas
          ┌──────────────▼──────────────────────────────┐
          │      GERADOR DE RELATÓRIO (report_generator) │
          │  Monta o .md final — números sempre do       │
          │  código, texto sempre do LLM validado        │
          └─────────────────────────────────────────────┘
```

### Decisão de design: separação de responsabilidades

O LLM **não calcula métricas** e **não decide quais tools chamar**. Essa separação foi uma escolha deliberada por duas razões:

1. **Confiabilidade numérica:** modelos locais de 7B consistentemente erram ou omitem valores percentuais quando precisam reproduzi-los com exatidão. As métricas são sempre compostas por código, a partir do retorno real das tools.
2. **Rastreabilidade:** cada etapa (carregamento de dados, execução de cada tool, prompt enviado, resposta recebida, resultado dos guardrails) é registrada no log de auditoria antes de prosseguir.

---

## Fluxo de Execução

```
orchestrator.executar_agente()
│
├── registrar_log("inicio_execucao")
├── carregar_base()                          → df (160MB, uma só leitura)
├── registrar_log("dados_carregados")
│
├── montar_dispatcher(df)
├── _chamar_todas_as_tools(dispatcher)
│   ├── calcular_mortalidade(df)  → registrar_log("tool_call:calcular_mortalidade")
│   ├── calcular_uti(df)          → registrar_log("tool_call:calcular_uti")
│   ├── calcular_vacinacao(df)    → registrar_log("tool_call:calcular_vacinacao")
│   ├── calcular_crescimento(df)  → registrar_log("tool_call:calcular_crescimento")
│   └── buscar_noticias()         → registrar_log("tool_call:buscar_noticias")
├── registrar_log("todas_tools_chamadas")
├── registrar_log("metricas_finais_usadas_no_relatorio")
│
├── _escrever_secoes(resultados, periodo_real)   → LLM (1 chamada)
│
├── validar_relatorio(texto, metricas)
├── registrar_log("validacao_guardrails")
│
├── [loop até 2x se reprovado]
│   ├── _regenerar_secoes(secoes, resultados, motivos)  → LLM (correção)
│   ├── validar_relatorio(...)
│   └── registrar_log("validacao_guardrails_apos_retentativa_N")
│
├── gerar_grafico_diario(df)
├── gerar_grafico_mensal(df)
│
├── montar_relatorio_final(secoes, metricas, validacao)
└── registrar_log("relatorio_gerado")
```

---

## Métricas Calculadas

Todas as métricas são funções Python que recebem o dataframe já carregado e retornam um dicionário — sem efeitos colaterais, sem recarregar o CSV.

| Métrica | Módulo | Descrição |
|---|---|---|
| **Taxa de mortalidade** | `metrics/mortality.py` | Óbitos / casos com evolução conhecida (`EVOLUCAO` preenchido) |
| **Taxa de UTI** | `metrics/uti.py` | Casos com passagem por UTI / registros com `UTI` preenchido. **Proxy**, não ocupação real de leitos. |
| **Taxa de vacinação** | `metrics/vaccination.py` | Vacinados / registros com `VACINA_COV` preenchido. Reflete os registros analisados, **não** cobertura populacional. |
| **Taxa de crescimento** | `metrics/growth_rate.py` | Casos nos últimos 30 dias vs. 30 dias anteriores, com âncora deslocada para excluir janela de imaturidade de notificação (ver abaixo). |

### Correção da taxa de crescimento

A base DATASUS tem um atraso mediano de ~7 dias entre o início dos sintomas (`DT_SIN_PRI`) e a digitação (`DT_DIGITA`). Usar a data máxima do arquivo como âncora incluía esse período incompleto, gerando uma queda artificial de casos — na versão anterior, o relatório exibia **−29,19%** quando a tendência real era de **+13,75%** (alta).

A correção desloca a âncora 10 dias para trás antes de calcular qualquer janela. O campo `aviso` no retorno da tool documenta esse ajuste explicitamente.

---

## Guardrails e Governança

### Guardrails programáticos (`src/utils/guardrails.py`)

O texto gerado pelo LLM passa por validação programática antes de entrar no relatório:

- **Termos proibidos:** diagnóstico clínico, recomendações de tratamento, interpretações econômicas/financeiras, referências a dados inexistentes na base (estado/UF, comorbidades, variantes de SARS-CoV-2).
- **Consistência direcional:** se a taxa de crescimento for positiva, o texto não pode afirmar "queda" — e vice-versa.
- **Disclaimers obrigatórios:** a taxa de UTI deve ser descrita como proxy; a taxa de vacinação deve referenciar os registros analisados, não a população; deve haver menção ao período de imaturidade de notificação.
- **Percentuais exatos:** o LLM é instruído a não citar percentuais — o guardrail verifica isso como camada adicional.

Se o texto reprovar, o orquestrador pede uma reescrita ao LLM (até 2 tentativas). Se ainda reprovar, o relatório é gerado com aviso visível.

### Auditoria (`src/utils/audit.py`)

Cada etapa do fluxo gera um registro em `logs/audit_log.json`:

```json
{
  "data_execucao": "2025-06-28T14:33:00.123456",
  "acao": "tool_call:calcular_mortalidade",
  "valor": {
    "taxa_mortalidade_pct": 7.73,
    "casos_avaliados": 142180,
    "obitos": 10990
  }
}
```

Ações registradas: `inicio_execucao`, `dados_carregados`, `tool_call:<nome>`, `todas_tools_chamadas`, `metricas_finais_usadas_no_relatorio`, `validacao_guardrails`, `validacao_guardrails_apos_retentativa_N`, `relatorio_gerado`, `falha_parse_json_llm`, `secoes_regeneradas`, `fallback_deterministico_acionado`.

---

## Estrutura do Repositório

```
srag-ai-engineer/
│
├── data/
│   └── raw/
│       └── INFLUD25_DATASUS-Versao26-06-2025.csv   # base original (não versionada)
│
├── logs/
│   └── audit_log.json          # gerado automaticamente a cada execução
│
├── outputs/
│   ├── relatorio_final.md
│   ├── daily_cases_30_days.png
│   └── monthly_cases_12_months.png
│
├── src/
│   ├── load_data.py            # carrega e limpa o CSV uma única vez
│   ├── clean_data.py           # exploratório (pode ser ignorado)
│   │
│   ├── agents/
│   │   ├── orchestrator.py     # ponto de entrada — executa o agente completo
│   │   ├── tools.py            # schemas e dispatcher das 5 tools
│   │   └── report_generator.py # monta o .md final a partir dos dados reais
│   │
│   ├── metrics/
│   │   ├── mortality.py
│   │   ├── uti.py
│   │   ├── vaccination.py
│   │   └── growth_rate.py
│   │
│   ├── news/
│   │   └── news_collector.py   # RSS via feedparser; retorna lista com categoria
│   │
│   ├── reports/
│   │   ├── daily_cases_chart.py
│   │   └── monthly_cases_chart.py
│   │
│   └── utils/
│       ├── audit.py            # registrar_log() — chamado em cada etapa
│       └── guardrails.py       # validação programática do texto do LLM
│
├── architecture_diagram.pdf
└── README.md
```

---

## Pré-requisitos e Instalação

### 1. Python

```bash
pip install pandas feedparser matplotlib
```

### 2. Ollama com modelo compatível com tool calling

O orquestrador usa `qwen2.5:7b` por padrão (mais consistente que `llama3` puro em seguir o protocolo de function calling).

```bash
# instalar Ollama: https://ollama.com
ollama pull qwen2.5:7b
```

Outros modelos compatíveis: `llama3.1`, `mistral-nemo`. Ajuste a constante `MODELO` em `orchestrator.py` se necessário.

### 3. Dados

Baixe o arquivo CSV em [Open DATASUS — SRAG 2021 a 2024](https://dadosabertos.saude.gov.br/dataset/srag-2021-a-2024) e salve em:

```
data/raw/INFLUD25_DATASUS-Versao26-06-2025.csv
```

---

## Como Executar

A partir da raiz do projeto (onde estão as pastas `data/`, `outputs/`, `logs/`):

```bash
python src/agents/orchestrator.py
```

O script imprime o progresso de cada etapa e, ao final, informa o caminho do relatório gerado. Se os guardrails detectarem problemas no texto do LLM, um aviso é exibido no terminal e registrado no relatório.

---

## Dados

**Fonte:** [Open DATASUS / SIVEP-Gripe](https://dadosabertos.saude.gov.br/dataset/srag-2021-a-2024), versão 26/06/2025.

**Colunas utilizadas:**

| Coluna | Descrição |
|---|---|
| `DT_SIN_PRI` | Data do primeiro sintoma |
| `DT_INTERNA` | Data de internação |
| `DT_EVOLUCA` | Data de evolução do caso |
| `DT_DIGITA` | Data de digitação no sistema |
| `SG_UF` | UF de notificação |
| `NU_IDADE_N` | Idade do paciente |
| `EVOLUCAO` | Evolução (1=cura, 2=óbito, ...) |
| `UTI` | Passou por UTI (1=sim, 2=não) |
| `VACINA_COV` | Vacinado contra COVID-19 (1=sim, 2=não) |

**Tratamento aplicado:**
- Seleção das colunas relevantes no momento da leitura (`usecols`) — reduz uso de memória do CSV de 160MB.
- Conversão das quatro colunas de data para `datetime` com `errors="coerce"` (datas inválidas viram `NaT`).
- Cada métrica filtra apenas os registros com o campo de interesse preenchido (`notna()`), evitando distorção por dados ausentes.
- A taxa de crescimento exclui os últimos 10 dias da base para compensar o atraso de notificação (ver seção de métricas).

---

## Saídas

| Arquivo | Descrição |
|---|---|
| `outputs/relatorio_final.md` | Relatório completo com as 4 métricas, correlação com notícias e texto qualitativo do LLM |
| `outputs/daily_cases_30_days.png` | Número diário de casos nos últimos 30 dias |
| `outputs/monthly_cases_12_months.png` | Número mensal de casos nos últimos 12 meses |
| `logs/audit_log.json` | Log completo de auditoria da execução |

---

## Limitações Conhecidas

- **Taxa de UTI** é uma proxy calculada sobre os registros com campo `UTI` preenchido. Não representa ocupação real de leitos de UTI no país.
- **Taxa de vacinação** reflete apenas os registros da base SRAG com `VACINA_COV` informado — não é equivalente à cobertura vacinal da população geral.
- **Dados recentes incompletos:** os últimos dias da base têm subnotificação por atraso de digitação. A taxa de crescimento compensa isso com âncora deslocada 10 dias; os gráficos exibem o período bruto e podem mostrar queda artificial nos últimos dias.
- **LLM local:** o texto qualitativo é gerado por um modelo de 7B rodando localmente via Ollama. A qualidade do texto depende do modelo instalado e pode variar entre execuções.
