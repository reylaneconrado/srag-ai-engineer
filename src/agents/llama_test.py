import subprocess

OLLAMA = r"C:\Users\MagelaConrado\AppData\Local\Programs\Ollama\ollama.exe"

prompt = """
Você é um analista de saúde pública.

Analise os indicadores:

Taxa de mortalidade: 7,73%
Taxa de UTI: 29,05%
Taxa de vacinação: 75,47%
Taxa de crescimento: -29,19%

Escreva um resumo executivo curto.
"""

resultado = subprocess.run(
    [OLLAMA, "run", "llama3"],
    input=prompt,
    text=True,
    capture_output=True,
    encoding="utf-8"
)

print(resultado.stdout)