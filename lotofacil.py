import pandas as pd
import random
import logging
from collections import defaultdict, Counter

# ---------------------------
# Função para carregar dados
# ---------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    try:
        df = pd.read_csv(file_path, sep=",")
        colunas = [f"Bola{i}" for i in range(1, 16)]
        if not all(c in df.columns for c in colunas):
            raise ValueError("Colunas inválidas no CSV (esperado Bola1...Bola15)")
        return df
    except Exception as e:
        print("Erro ao carregar dados:", e)
        return None

# ---------------------------
# Frequência de dezenas
# ---------------------------
def calcular_frequencia(df, ultimos=100):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    dados = df.tail(ultimos)[dezenas_cols]
    contagem = Counter(dados.values.flatten())
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    return ranking

# ---------------------------
# Dezenas atrasadas
# ---------------------------
def calcular_atrasos(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    atrasos = {d: 0 for d in range(1, 26)}
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}

    # Percorre concursos de trás pra frente
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
# Pares e Ímpares
# ---------------------------
def calcular_pares_impares(df, ultimos=100):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    stats = Counter()

    for _, row in df.tail(ultimos).iterrows():
        dezenas = row[dezenas_cols].values
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = 15 - pares
        stats[(pares, impares)] += 1

    return pd.DataFrame(
        [(pares, impares, qtd) for (pares, impares), qtd in stats.items()],
        columns=["Pares", "Ímpares", "Ocorrências"]
    ).sort_values("Ocorrências", ascending=False)

# ---------------------------
# Sequências
# ---------------------------
def calcular_sequencias(df, ultimos=100):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    stats = Counter()

    for _, row in df.tail(ultimos).iterrows():
        dezenas = sorted(row[dezenas_cols].values)
        seq = 1
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i-1] + 1:
                seq += 1
            else:
                if seq >= 2:
                    stats[seq] += 1
                seq = 1
        if seq >= 2:
            stats[seq] += 1

    return pd.DataFrame(
        [(tam, qtd) for tam, qtd in stats.items()],
        columns=["Tamanho da Sequência", "Ocorrências"]
    ).sort_values("Tamanho da Sequência")

# ---------------------------
# Gerar jogos com base nas dezenas fixas e base
# ---------------------------
def gerar_jogos(dezenas_base, qtd_15=0, qtd_16=0, qtd_17=0, qtd_18=0, dezenas_fixas=None):
    jogos = []
    dezenas_fixas = dezenas_fixas or []

    if len(dezenas_fixas) > 11:
        raise ValueError("As dezenas fixas devem ter no máximo 11 números.")

    # Função interna para criar um jogo
    def criar_jogo(tamanho):
        jogo = set(dezenas_fixas)
        while len(jogo) < tamanho:
            jogo.add(random.choice(dezenas_base))
        return sorted(jogo)

    for _ in range(qtd_15):
        jogos.append(criar_jogo(15))
    for _ in range(qtd_16):
        jogos.append(criar_jogo(16))
    for _ in range(qtd_17):
        jogos.append(criar_jogo(17))
    for _ in range(qtd_18):
        jogos.append(criar_jogo(18))

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
