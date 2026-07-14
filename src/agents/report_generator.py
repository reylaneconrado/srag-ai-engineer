import os
import json
import urllib.request
from datetime import datetime


OLLAMA = r"C:\Users\MagelaConrado\AppData\Local\Programs\Ollama\ollama.exe"

OUTPUT_FILE = "outputs/relatorio_final.md"

metricas = {
    "taxa_mortalidade": "7,73%",
    "casos_avaliados_mortalidade": "127.927",
    "obitos": "9.885",
    "taxa_uti": "29,05%",
    "casos_uti": "42.519",
    "registros_uti": "146.386",
    "taxa_vacinacao": "75,47%",
    "vacinados": "124.808",
    "registros_vacinacao": "165.372",
    "taxa_crescimento": "-29,19%",
    "casos_ultimos_30_dias": "35.578",
    "casos_30_dias_anteriores": "50.242"
}

noticias = [
    "Severe Acute Respiratory Syndrome (SARS) - World Health Organization (WHO)",
    "Regional Workshop in Brazil Enhances Capacity to Measure Influenza Burden and Vaccination Impact - PAHO/WHO",
    "Avian flu reported in Brazil, Colombia backyard birds",
    "Vaccination inequality and social determinants in Brazil during the COVID-19 pandemic",
    "Zoonotic transmission of novel Influenza A variant viruses detected in Brazil during 2020 to 2023"
]

prompt = f"""
Você é um agente de Inteligência Artificial especializado em análise epidemiológica e geração de relatórios executivos.

Contexto obrigatório:
SRAG significa Síndrome Respiratória Aguda Grave.
O relatório usa dados públicos do Open DATASUS/SIVEP-Gripe.
As métricas são agregadas e não representam diagnóstico individual.

Regras obrigatórias:
- Não invente informações.
- Não diga que uma métrica representa economia, finanças ou orçamento.
- Não faça diagnóstico médico.
- Não recomende tratamento clínico.
- Explique limitações dos dados.
- Use linguagem profissional.
- Seja claro e objetivo.
- A taxa de crescimento negativa significa redução de casos, não crise econômica.
- A métrica de UTI é uma proxy de utilização de UTI entre casos SRAG, não ocupação real de leitos.
- A taxa de vacinação representa vacinação entre os registros analisados, não cobertura populacional geral.

Métricas calculadas:
- Taxa de mortalidade: {metricas["taxa_mortalidade"]}
- Casos avaliados para mortalidade: {metricas["casos_avaliados_mortalidade"]}
- Óbitos: {metricas["obitos"]}

- Taxa de casos com UTI: {metricas["taxa_uti"]}
- Casos com UTI: {metricas["casos_uti"]}
- Registros com informação de UTI: {metricas["registros_uti"]}

- Taxa de vacinação: {metricas["taxa_vacinacao"]}
- Registros vacinados: {metricas["vacinados"]}
- Registros com informação de vacinação: {metricas["registros_vacinacao"]}

- Taxa de crescimento dos casos: {metricas["taxa_crescimento"]}
- Casos nos últimos 30 dias: {metricas["casos_ultimos_30_dias"]}
- Casos nos 30 dias anteriores: {metricas["casos_30_dias_anteriores"]}

Notícias e fontes externas coletadas:
{chr(10).join(["- " + noticia for noticia in noticias])}

Gere um relatório em Markdown com esta estrutura:

# Relatório Analítico de SRAG

## 1. Resumo Executivo

## 2. Métricas Principais

### 2.1 Taxa de Mortalidade

### 2.2 Taxa de Casos com UTI

### 2.3 Taxa de Vacinação

### 2.4 Taxa de Crescimento dos Casos

## 3. Contexto Externo com Notícias

## 4. Limitações da Análise

## 5. Governança e Transparência

## 6. Conclusão

Inclua também uma observação final dizendo que o relatório tem finalidade analítica e informativa.
"""

def chamar_llama(prompt):
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["response"]


relatorio_ia = chamar_llama(prompt)


conteudo_final = f"""# Relatório Analítico de SRAG

Data de geração: {datetime.now().strftime("%d/%m/%Y %H:%M")}

---

{relatorio_ia}

---

## Arquivos Gerados

- Gráfico diário dos últimos 30 dias: `outputs/daily_cases_30_days.png`
- Gráfico mensal dos últimos 12 meses: `outputs/monthly_cases_12_months.png`

---

## Observação Técnica

Este relatório foi gerado automaticamente por uma solução de Inteligência Artificial utilizando:

- Dados estruturados do Open DATASUS/SIVEP-Gripe
- Métricas calculadas em Python
- Consulta de notícias via RSS
- Modelo Llama3 executado localmente com Ollama
- Guardrails para evitar interpretações clínicas indevidas ou extrapolações não suportadas pelos dados
"""

os.makedirs("outputs", exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(conteudo_final)

print("Relatório final gerado com sucesso!")
print(f"Arquivo salvo em: {OUTPUT_FILE}")