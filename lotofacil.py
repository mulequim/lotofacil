import pandas as pd
import random
import logging
from collections import defaultdict

# ---------------------------
# Carregar dados
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
# Atrasos
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
# Gerar jogos detalhados
# ---------------------------
def gerar_jogos(
    dezenas_base, qtd_15=0, qtd_16=0, qtd_17=0, qtd_18=0, dezenas_fixas=None, atrasadas=None
):
    jogos = []
    dezenas_fixas = dezenas_fixas or []
    atrasadas = atrasadas or []

    if len(dezenas_fixas) > 11:
        raise ValueError("As dezenas fixas devem ter no máximo 11 números.")

    # completar fixas automáticas (top base) até 11
    fixas_auto = []
    if len(dezenas_fixas) < 11:
        for d in dezenas_base:
            if d not in dezenas_fixas and len(dezenas_fixas) + len(fixas_auto) < 11:
                fixas_auto.append(d)

    # Função para criar jogo
    def criar_jogo(tamanho):
        jogo = []
        origem = {}

        # fixas do usuário
        for d in dezenas_fixas:
            jogo.append(d)
            origem[d] = "fixa_usuario"

        # fixas automáticas
        for d in fixas_auto:
            if len(jogo) < tamanho:
                jogo.append(d)
                origem[d] = "fixa_auto"

        # atrasadas
        for d in atrasadas:
            if len(jogo) < tamanho and d not in jogo:
                jogo.append(d)
                origem[d] = "atrasada"

        # completar com base
        while len(jogo) < tamanho:
            d = random.choice(dezenas_base)
            if d not in jogo:
                jogo.append(d)
                origem[d] = "base"

        return sorted(jogo), origem

    # gerar jogos
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

    for idx, (jogo, origem) in enumerate(jogos, start=1):
        contagens = {11:0, 12:0, 13:0, 14:0, 15:0}
        for _, row in df.iterrows():
            sorteadas = set(row[dezenas_cols].values)
            acertos = len(sorteadas & set(jogo))
            if acertos >= 11:
                contagens[acertos] += 1
        resultados.append((idx, jogo, contagens))
    return resultados
