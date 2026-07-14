# SRAG AI Engineer - Indicium Certification

## Visão Geral

Este projeto foi desenvolvido como parte da Certificação Artificial Intelligence Engineer by Indicium AI.

O objetivo da solução é criar uma Prova de Conceito (PoC) capaz de analisar dados públicos sobre Síndrome Respiratória Aguda Grave (SRAG), gerar métricas epidemiológicas, coletar informações de fontes externas e produzir relatórios automáticos utilizando Inteligência Artificial Generativa.

A solução utiliza dados do Open DATASUS/SIVEP-Gripe e demonstra como agentes de IA podem apoiar processos de análise epidemiológica por meio da combinação de dados estruturados, notícias externas e Large Language Models (LLMs).

---

# Objetivos

A solução foi desenvolvida para:

- Calcular indicadores epidemiológicos relevantes.
- Gerar visualizações analíticas.
- Consultar notícias em tempo real relacionadas a SRAG.
- Utilizar um LLM para interpretar métricas e contexto externo.
- Gerar relatórios automaticamente.
- Demonstrar boas práticas de governança, transparência e uso responsável de IA.

---

# Fonte de Dados

Base utilizada:

Open DATASUS / SIVEP-Gripe

Arquivo:

```text
INFLUD25_DATASUS-Versao26-06-2025.csv
```

Características da base:

- 165.397 registros
- 194 colunas
- Dados reais de notificação de SRAG
- Dados públicos disponibilizados pelo Ministério da Saúde

---

# Arquitetura da Solução

```text
                +----------------+
                |     Usuário    |
                +--------+-------+
                         |
                         v
             +-----------+------------+
             | Agente Orquestrador    |
             +-----------+------------+
                         |
       +----------------+----------------+
       |                |                |
       v                v                v

+-------------+  +-------------+  +-------------+
| Métricas    |  | Notícias    |  | Gráficos    |
| Epidemiol.  |  | RSS Google  |  | Matplotlib  |
+------+------+  +------+------+  +------+------+
       |                |                |
       +----------------+----------------+
                        |
                        v

                +--------------+
                |   Llama3     |
                |   Ollama     |
                +------+-------+
                       |
                       v

             +-------------------+
             | Relatório Final   |
             +-------------------+
```

---

# Estrutura do Projeto

```text
srag-ai-engineer/

├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── agents/
│   ├── metrics/
│   ├── news/
│   ├── reports/
│   └── utils/
│
├── outputs/
│
├── tests/
│
├── README.md
├── requirements.txt
└── main.py
```

---

# Métricas Calculadas

## Taxa de Mortalidade

Resultado:

```text
7,73%
```

Metodologia:

A taxa foi calculada considerando apenas registros com evolução conhecida.

```text
Óbitos / Casos com evolução conhecida
```

Resultado:

- Casos avaliados: 127.927
- Óbitos: 9.885

---

## Taxa de Casos com UTI

Resultado:

```text
29,05%
```

Metodologia:

Proporção de pacientes SRAG que necessitaram de internação em UTI.

Observação:

A base não contém informações sobre capacidade hospitalar.

Portanto:

Esta métrica representa uma proxy de utilização de UTI entre casos SRAG e não ocupação real de leitos.

Resultado:

- Casos com UTI: 42.519
- Registros analisados: 146.386

---

## Taxa de Vacinação

Resultado:

```text
75,47%
```

Metodologia:

Proporção de indivíduos vacinados entre os registros analisados.

Observação:

Não representa cobertura vacinal da população geral.

Resultado:

- Registros vacinados: 124.808
- Registros analisados: 165.372

---

## Taxa de Crescimento dos Casos

Resultado:

```text
-29,19%
```

Metodologia:

Comparação entre:

- Últimos 30 dias
- 30 dias imediatamente anteriores

Resultado:

- Casos últimos 30 dias: 35.578
- Casos 30 dias anteriores: 50.242

Interpretação:

Houve redução de casos registrados no período mais recente.

---

# Visualizações

## Casos Diários (Últimos 30 Dias)

Arquivo:

```text
outputs/daily_cases_30_days.png
```

---

## Casos Mensais (Últimos 12 Meses)

Arquivo:

```text
outputs/monthly_cases_12_months.png
```

---

# Consulta de Notícias

A solução utiliza RSS do Google News para coletar notícias relacionadas a:

- Síndrome Respiratória Aguda Grave
- Influenza
- COVID-19
- Vírus respiratórios

Essas informações são utilizadas como contexto adicional para interpretação dos indicadores calculados.

---

# Inteligência Artificial Generativa

Foi utilizado:

```text
Llama3
```

executado localmente através do:

```text
Ollama
```

Funções do modelo:

- Interpretação dos indicadores
- Contextualização dos resultados
- Geração automática do relatório final
- Geração de conclusões executivas

---

# Governança e Transparência

A solução segue princípios de IA Responsável:

## Transparência

Todas as métricas possuem metodologia documentada.

## Explicabilidade

Os resultados apresentados podem ser rastreados até as consultas realizadas na base.

## Auditabilidade

Os indicadores gerados possuem origem identificável e reproduzível.

## Reprodutibilidade

Toda a solução pode ser executada localmente utilizando os scripts disponibilizados.

---

# Guardrails Implementados

A solução possui restrições para:

- Evitar diagnósticos médicos.
- Evitar recomendações clínicas.
- Evitar extrapolações não suportadas pelos dados.
- Informar limitações analíticas.
- Diferenciar indicadores observados de inferências.

---

# Tratamento de Dados Sensíveis

Apesar de a base ser pública e anonimizada, foram adotadas práticas de minimização de dados:

- Uso apenas das colunas necessárias.
- Análises realizadas em nível agregado.
- Nenhuma identificação individual é realizada.
- Nenhum dado pessoal é exposto nos relatórios.

---

# Relatório Gerado

Arquivo:

```text
outputs/relatorio_final.md
```

O relatório é gerado automaticamente combinando:

- Métricas epidemiológicas
- Fontes externas
- Interpretação por IA
- Regras de governança

---

# Tecnologias Utilizadas

- Python
- Pandas
- Matplotlib
- Feedparser
- Ollama
- Llama3
- RSS Google News

---

# Possíveis Evoluções

- Integração com LangChain
- Integração com LangGraph
- Banco vetorial para RAG
- Banco PostgreSQL
- Databricks
- Dashboard Web
- Monitoramento contínuo

---

# Autor

Mágela Reylane Cruz Conrado

Projeto desenvolvido para obtenção da Certificação Artificial Intelligence Engineer by Indicium AI.