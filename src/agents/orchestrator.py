"""Agente Orquestrador.

Depois de muitas rodadas de teste reais (llama3.1 e qwen2.5:7b, com e sem
temperatura baixa), ficou claro que pedir para o LLM redigir E reproduzir
com fidelidade 4 números percentuais ao mesmo tempo tem um teto de erro
que não cai a zero com prompt engineering — o modelo local
consistentemente errava ou omitia 1-2 das 4 métricas.

Por isso o desenho final SEPARA as duas responsabilidades:
  - Os números da seção "Métricas Principais" são sempre montados por
    CÓDIGO (ver report_generator.py), a partir do que as tools realmente
    retornaram. Isso é garantido, nunca erra.
  - O LLM escreve SÓ o texto qualitativo (resumo executivo, contexto de
    notícias, limitações, governança, conclusão) em formato JSON
    estruturado, e é instruído a não repetir os percentuais exatos —
    exatamente o tipo de tarefa em que um modelo de 7B local é confiável.

O restante do fluxo continua o mesmo: as 5 tools são sempre chamadas por
código (nunca depende do LLM decidir), os guardrails validam o texto
gerado, e há até 2 tentativas de correção antes de aceitar com aviso.
"""

import json
import re
import sys
import urllib.request

sys.path.insert(0, "src")  # permite rodar tanto de dentro de src/ quanto da raiz

from load_data import carregar_base
from agents.tools import montar_dispatcher
from utils.audit import registrar_log
from utils.guardrails import validar_relatorio
from reports.daily_cases_chart import gerar_grafico_diario
from reports.monthly_cases_chart import gerar_grafico_mensal
from agents.report_generator import montar_relatorio_final

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODELO = "qwen2.5:7b"  # testado como mais consistente do que o llama3.1 puro

TOOLS_OBRIGATORIAS = [
    "calcular_mortalidade",
    "calcular_uti",
    "calcular_vacinacao",
    "calcular_crescimento",
    "buscar_noticias",
]

CHAVES_SECOES = ["resumo_executivo", "contexto_noticias", "limitacoes", "governanca", "conclusao"]

SYSTEM_PROMPT = """Você é um agente de Inteligência Artificial especializado em análise \
epidemiológica e geração de relatórios executivos sobre SRAG (Síndrome Respiratória Aguda \
Grave), com base em dados públicos do Open DATASUS/SIVEP-Gripe.

Você vai receber os dados JÁ CALCULADOS pelas ferramentas do agente. Sua tarefa é escrever \
APENAS o texto qualitativo do relatório — os números exatos das 4 métricas principais \
(mortalidade, UTI, vacinação, crescimento) já são inseridos automaticamente em outra seção do \
documento, que você NÃO escreve.

Regra mais importante: NUNCA cite um percentual específico (ex.: "7,73%") no texto que você \
escrever. Você pode comentar a DIREÇÃO ou magnitude qualitativa (ex.: "a mortalidade se mostrou \
relevante", "houve alta no número de casos"), mas nunca o número exato — isso evita qualquer \
risco de você citar um valor diferente do calculado.

Este agente tem EXATAMENTE 4 métricas disponíveis: mortalidade, UTI, vacinação e crescimento de \
casos. NÃO existe nenhum dado sobre distribuição por estado/UF, taxa de casos por região, \
prevalência de comorbidades, taxa de confirmação por SARS-CoV-2/variantes, ou qualquer outra \
quebra demográfica ou clínica. Não mencione nenhuma dessas categorias.

Regras obrigatórias:
- Não faça diagnóstico médico nem recomende tratamento clínico.
- Não interprete nenhuma métrica em termos econômicos, financeiros ou de orçamento.
- A métrica de UTI é uma proxy de utilização de UTI entre casos SRAG, não ocupação real de leitos.
- A taxa de vacinação representa vacinação entre os registros analisados, não cobertura \
populacional geral.
- NUNCA invente um período/intervalo de datas. Use exclusivamente o período informado a você.
- Se a lista de notícias vier vazia, apenas informe que nenhuma notícia foi encontrada. Não \
invente motivos.
- Use linguagem profissional, clara e objetiva.

Responda APENAS com um objeto JSON válido, sem blocos de código markdown (nada de ```), sem \
texto antes ou depois, com EXATAMENTE estas chaves — cada uma um texto em Markdown simples (sem \
cabeçalhos "#"):

{
  "resumo_executivo": "...",
  "contexto_noticias": "...",
  "limitacoes": "...",
  "governanca": "...",
  "conclusao": "..."
}
"""


def _chamar_ollama_chat(mensagens):
    payload = {
        "model": MODELO,
        "messages": mensagens,
        "stream": False,
        # Temperatura baixa = respostas mais "determinísticas" e menos
        # propensas a inventar números/categorias que não vieram dos dados.
        "options": {"temperature": 0.1},
    }

    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extrair_json(resposta_texto: str) -> dict:
    """Extrai o objeto JSON da resposta do modelo, tolerando texto extra
    antes/depois (cercas de código markdown, comentários do modelo após o
    JSON etc.) — em vez de só remover cercas na ponta exata da string
    (o que falhava quando o modelo escrevia algo como "```json{...}```
    Observação: ..." com texto depois da cerca de fechamento).
    Encontra o primeiro '{' e sua chave de fechamento correspondente
    (contando profundidade de chaves), e tenta fazer o parse só desse
    trecho.
    """
    texto = resposta_texto.strip()
    inicio = texto.find("{")

    dados = None
    if inicio != -1:
        profundidade = 0
        fim = -1
        for i in range(inicio, len(texto)):
            if texto[i] == "{":
                profundidade += 1
            elif texto[i] == "}":
                profundidade -= 1
                if profundidade == 0:
                    fim = i
                    break
        if fim != -1:
            try:
                dados = json.loads(texto[inicio:fim + 1])
            except json.JSONDecodeError:
                dados = None

    if dados is None:
        # Fallback: se não achou um objeto JSON válido em lugar nenhum, usa
        # o texto inteiro como resumo executivo e deixa o resto vazio — o
        # guardrail ainda roda sobre esse texto normalmente.
        registrar_log(acao="falha_parse_json_llm", valor=resposta_texto[:500])
        dados = {"resumo_executivo": texto}

    return {chave: _paragrafar(dados.get(chave, "")) for chave in CHAVES_SECOES}


def _paragrafar(valor) -> str:
    """Converte o valor de uma seção em texto legível, MESMO quando o
    modelo (contra a instrução) aninha um dict/list em vez de escrever uma
    string simples — foi o que aconteceu na prática (o modelo colocou
    sub-chaves como "taxa_mortalidade", "utilizacao_uti" dentro de
    "resumo_executivo"). Sem isso, um `str(dict)` cru vira um bloco de
    texto sem quebras de linha, o que quebra a checagem de "parágrafo" dos
    guardrails (tudo cai num único bloco enorme).
    Cada item de dict/list vira seu próprio parágrafo, separado por linha
    em branco — assim os guardrails conseguem isolar cada trecho.
    """
    if isinstance(valor, dict):
        return "\n\n".join(_paragrafar(v) for v in valor.values())
    if isinstance(valor, list):
        return "\n\n".join(_paragrafar(v) for v in valor)
    return str(valor)


def _chamar_todas_as_tools(dispatcher: dict) -> dict:
    """Chama as 5 tools obrigatórias diretamente, por código — não depende
    do LLM decidir. Isso é o que garante que o relatório sempre reflita
    dados reais, sem risco de "tool pulada" ou "tool esquecida".
    """
    resultados = {}
    for nome in TOOLS_OBRIGATORIAS:
        print(f"[orquestrador]   -> chamando tool: {nome}")
        resultados[nome] = dispatcher[nome]()
    return resultados


def _escrever_secoes(resultados: dict, periodo_real: str) -> dict:
    """Única chamada ao LLM: recebe os dados reais e completos e escreve
    só o texto qualitativo, em JSON estruturado (ver CHAVES_SECOES).
    """
    prompt = (
        f"Período real dos dados analisados: {periodo_real}. Use exatamente esse período "
        "se precisar mencioná-lo — nunca invente outro.\n\n"
        "Aqui estão os dados reais, já calculados por todas as ferramentas (você NÃO deve "
        "repetir os percentuais exatos no seu texto, isso já é feito automaticamente em outra "
        f"seção):\n{json.dumps(resultados, ensure_ascii=False, default=str)}\n"
    )

    resposta = _chamar_ollama_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])
    return _extrair_json(resposta["message"]["content"])


def _regenerar_secoes(secoes_anteriores: dict, resultados: dict, motivos: list[str]) -> dict:
    """Pede ao LLM para reescrever as seções quando os guardrails reprovam
    o texto (termos proibidos, número indevido nas seções qualitativas,
    categorias fora de escopo etc.).
    """
    dados_reais = json.dumps(resultados, ensure_ascii=False, default=str)
    motivos_txt = "\n".join(f"- {m}" for m in motivos)

    prompt_correcao = (
        "O rascunho de texto abaixo (em JSON) tem os seguintes problemas identificados de "
        f"forma automática e precisa ser reescrito:\n{motivos_txt}\n\n"
        f"Aqui estão os dados reais e completos:\n{dados_reais}\n\n"
        "Reescreva as 5 seções (mesmo formato JSON). Lembre-se: NUNCA cite um percentual "
        "específico das 4 métricas — isso é feito automaticamente em outra parte do relatório. "
        "NÃO adicione nenhuma categoria de dado que não esteja no JSON de dados acima (nada de "
        "estado/UF, região, comorbidades, ou SARS-CoV-2/variantes).\n\n"
        "Rascunho anterior (pode conter erros):\n" + json.dumps(secoes_anteriores, ensure_ascii=False)
    )

    resposta = _chamar_ollama_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_correcao},
    ])
    registrar_log(acao="secoes_regeneradas", valor={"motivos": motivos})
    return _extrair_json(resposta["message"]["content"])


def _normalizar_metricas(resultados: dict) -> dict:
    return {
        "mortalidade": resultados.get("calcular_mortalidade", {}),
        "uti": resultados.get("calcular_uti", {}),
        "vacinacao": resultados.get("calcular_vacinacao", {}),
        "crescimento": resultados.get("calcular_crescimento", {}),
        "noticias": resultados.get("buscar_noticias", []),
    }


def executar_agente():
    registrar_log(acao="inicio_execucao", valor=True)

    print("[orquestrador] Carregando base de dados (pode levar um tempo)...")
    df = carregar_base()
    print(f"[orquestrador] Base carregada: {len(df)} linhas.")
    registrar_log(acao="dados_carregados", valor={"linhas": len(df)})

    dispatcher = montar_dispatcher(df)
    periodo_real = f"{df['DT_SIN_PRI'].min().date()} a {df['DT_SIN_PRI'].max().date()}"

    print("[orquestrador] Chamando as 5 tools (execução determinística)...")
    resultados = _chamar_todas_as_tools(dispatcher)
    registrar_log(acao="todas_tools_chamadas", valor=list(resultados.keys()))

    metricas = _normalizar_metricas(resultados)
    registrar_log(acao="metricas_finais_usadas_no_relatorio", valor=metricas)

    print(f"[orquestrador] Consultando modelo ({MODELO}) para redigir o texto qualitativo...")
    secoes = _escrever_secoes(resultados, periodo_real)

    texto_para_validar = "\n\n".join(secoes.values())
    validacao = validar_relatorio(texto_para_validar, metricas, texto_noticias=secoes.get("contexto_noticias", ""))
    registrar_log(acao="validacao_guardrails", valor=validacao)

    MAX_TENTATIVAS_CORRECAO = 2
    tentativa = 0
    while not validacao["aprovado"] and tentativa < MAX_TENTATIVAS_CORRECAO:
        tentativa += 1
        print(f"[orquestrador] Guardrails reprovaram o texto ({len(validacao['problemas'])} problema(s)), tentativa de correção {tentativa}/{MAX_TENTATIVAS_CORRECAO}...")
        secoes = _regenerar_secoes(secoes, resultados, validacao["problemas"])
        texto_para_validar = "\n\n".join(secoes.values())
        validacao = validar_relatorio(texto_para_validar, metricas, texto_noticias=secoes.get("contexto_noticias", ""))
        registrar_log(acao=f"validacao_guardrails_apos_retentativa_{tentativa}", valor=validacao)

    print("[orquestrador] Gerando gráficos...")
    gerar_grafico_diario(df)
    gerar_grafico_mensal(df)

    caminho = montar_relatorio_final(
        secoes=secoes,
        metricas=metricas,
        validacao_guardrails=validacao,
    )

    registrar_log(acao="relatorio_gerado", valor={"arquivo": caminho, "aprovado_guardrails": validacao["aprovado"]})

    print("Relatório final gerado com sucesso!")
    print(f"Arquivo salvo em: {caminho}")
    if not validacao["aprovado"]:
        print("\n⚠️  ATENÇÃO — guardrails encontraram problemas no texto gerado pelo LLM:")
        for problema in validacao["problemas"]:
            print(f"  - {problema}")


if __name__ == "__main__":
    executar_agente()
