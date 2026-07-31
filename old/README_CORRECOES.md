# Correções aplicadas ao srag-ai-engineer


## 1. Descoberta importante: a taxa de crescimento estava invertida

Os dados vão até **25/06/2025**, mas há um atraso mediano de **7 dias** entre a data
de início de sintomas e a data de digitação no sistema (`DT_DIGITA`). Isso significa
que os ~10 últimos dias da base sempre vão parecer ter poucos casos, mesmo que a
tendência real seja de alta — os registros ainda não foram todos digitados.

O `growth_rate.py` original comparava "últimos 30 dias" direto contra a última data
do arquivo, capturando esse artefato. Resultado: o relatório dizia **-29,19% (queda)**.

Recalculando com uma âncora que exclui os últimos 10 dias imaturos, a taxa real é
**+13,75% (alta)** — o oposto do que estava sendo reportado. Testei isso com a base
real que veio no seu zip.

As outras 3 métricas (mortalidade 7,73%, UTI 29,05%, vacinação 75,47%) bateram
exatamente com o que já estava no seu relatório — essas estavam corretas.

## 2. O que foi reconstruído

| Arquivo | O que mudou |
|---|---|
| `src/load_data.py` | Novo. Carrega e limpa o CSV **uma vez só** (antes, 6 scripts diferentes recarregavam o arquivo de 160MB cada um). |
| `src/metrics/*.py` | Cada métrica virou uma função que **retorna um dict**, em vez de um script que só imprime. Isso é o que permite o agente chamá-las como tools. |
| `src/metrics/growth_rate.py` | Corrigido: exclui a janela de imaturidade de notificação (10 dias) antes de calcular. Retorna também um campo `aviso` explicando a limitação. |
| `src/news/news_collector.py` | Mantido (já estava funcional), mas agora cada notícia carrega uma `categoria` para poder ser correlacionada com a métrica correspondente no relatório. |
| `src/utils/audit.py` | Mesma lógica, mas agora **é de fato chamada** pelo orquestrador em cada etapa (carregar dados, cada tool, validação, geração do relatório). |
| `src/utils/guardrails.py` | **Novo.** Validação programática do texto gerado pelo LLM: bloqueia termos indevidos (diagnóstico, "crise econômica" etc.), checa se a direção da taxa de crescimento no texto bate com o sinal real calculado, e confere se os disclaimers obrigatórios (UTI é proxy, vacinação é amostra, dados recentes imaturos) estão presentes. |
| `src/agents/tools.py` | **Novo.** Define o schema das tools (formato de tool-calling do Ollama) e um dispatcher que executa cada uma e loga na auditoria. |
| `src/agents/orchestrator.py` | **Reconstruído do zero.** Antes só tinha um `print()`. Agora carrega os dados, roda um loop real de tool-calling com o Ollama (o modelo decide quais tools chamar), tem um **fallback determinístico** caso o modelo não use tool calling (nunca cai para dados hardcoded), roda os guardrails, gera os gráficos e o relatório. |
| `src/agents/report_generator.py` | Reescrito para **não ter nenhum valor hardcoded** — monta o relatório a partir do que as tools realmente retornaram na execução, e mostra um aviso visível se os guardrails reprovarem o texto. |
| `src/reports/*_chart.py` | Viraram funções que recebem o dataframe já carregado, em vez de recarregar o CSV. |

## 3. Antes de rodar

1. **Instale um modelo com suporte a tool calling no Ollama.** O `llama3` (3.0) puro
   não segue bem o protocolo de function calling. Recomendo:
   ```
   ollama pull llama3.1
   ```
   (já deixei `MODELO = "llama3.1"` configurado em `orchestrator.py` — ajuste se
   preferir outro modelo compatível, como `qwen2.5` ou `mistral-nemo`).

2. Instale a dependência que faltava:
   ```
   pip install feedparser
   ```

3. Rode a partir da raiz do projeto (onde estão as pastas `data/`, `outputs/`, `logs/`):
   ```
   python src/agents/orchestrator.py
   ```

## 4. O que testei aqui (sem acesso a rede/Ollama neste ambiente)

- As 4 métricas contra a base real do seu zip (valores acima).
- O fluxo completo do orquestrador (loop de tool calling, fallback, guardrails,
  geração de relatório e gráficos) com um LLM simulado — inclusive testei
  propositalmente o mesmo erro do relatório original (dizer "queda" quando é alta,
  mencionar "crise econômica", omitir os disclaimers) e os guardrails pegaram os
  5 problemas corretamente.
- **Não testei** a chamada real ao Ollama/tool-calling do `llama3.1`, porque este
  ambiente não tem rede nem Ollama instalado. Vale rodar localmente e conferir se o
  modelo de fato emite `tool_calls` — se não emitir, o fallback determinístico entra
  em ação automaticamente (você verá um registro `fallback_deterministico_acionado`
  no log de auditoria).

## 5. Ainda vale melhorar (não fiz porque exigiria mais decisões suas)

- `clean_data.py` ficou redundante com `load_data.py` — pode remover ou transformar
  num notebook exploratório.
- O tratamento de dados continua limitado a seleção de colunas + conversão de datas.
  Vale avaliar outliers de idade (`NU_IDADE_N`), valores fora do dicionário de
  domínio do DATASUS em `EVOLUCAO`/`UTI`/`VACINA_COV`, e duplicatas.
