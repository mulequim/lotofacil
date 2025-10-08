import pandas as pd
from github import Github
import requests
import base64
import os
import random
from collections import Counter
from itertools import combinations

# ---------------------------
# Carregar dados do CSV
# ---------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    df = pd.read_csv(file_path, sep=",")
    return df

# ---------------------------
# Calcular frequência das dezenas
# ---------------------------
def calcular_frequencia(df, ultimos=100):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    dados = df.tail(ultimos)[dezenas_cols]
    contagem = Counter(dados.values.flatten())
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    return ranking

# ---------------------------
# Calcular atrasos das dezenas
# ---------------------------
def calcular_atrasos(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}

    for _, row in df[::-1].iterrows():
        sorteadas = set(row[dezenas_cols].values)
        for d in range(1, 26):
            if d not in sorteadas:
                atual_atraso[d] += 1
            else:
                max_atrasos[d] = max(max_atrasos[d], atual_atraso[d])
                atual_atraso[d] = 0

    dados = []
    for d in range(1, 26):
        dados.append([d, max_atrasos[d], atual_atraso[d]])

    return pd.DataFrame(dados, columns=["Dezena", "Máx Atraso", "Atraso Atual"])

# ---------------------------
# Gerar jogos
# ---------------------------
def gerar_jogos(dezenas_base, qtd_jogos=4, tamanho_jogo=15, dezenas_fixas=None, atrasadas=None):
    jogos = []
    dezenas_fixas = dezenas_fixas or []
    atrasadas = atrasadas or []

    for _ in range(qtd_jogos):
        jogo = set(dezenas_fixas)
        while len(jogo) < tamanho_jogo:
            d = random.choice(dezenas_base)
            jogo.add(d)
        jogos.append(sorted(jogo))
    return jogos

# ---------------------------
# Avaliar jogos contra histórico
# ---------------------------
def avaliar_jogos(jogos, df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    resultados = []
    for idx, jogo in enumerate(jogos, start=1):
        contagens = {11:0, 12:0, 13:0, 14:0, 15:0}
        for _, row in df.iterrows():
            sorteadas = set(row[dezenas_cols].values)
            acertos = len(sorteadas & set(jogo))
            if acertos >= 11:
                contagens[acertos] += 1
        resultados.append((idx, jogo, contagens))
    return resultados

# ---------------------------
# Obter concurso atual da API Caixa
# ---------------------------
def obter_concurso_atual_api():
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "numero": data["numero"],
                "dataApuracao": data["dataApuracao"],
                "dezenas": [int(d) for d in data["listaDezenas"]],
            }
    except Exception:
        return None
