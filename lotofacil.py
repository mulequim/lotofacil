import pandas as pd
import random
from collections import Counter

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
# Equilíbrio de pares e ímpares
# ---------------------------
def equilibrar_pares_impares(jogo, dezenas_base):
    pares = [d for d in dezenas_base if d % 2 == 0 and d not in jogo]
    impares = [d for d in dezenas_base if d % 2 != 0 and d not in jogo]

    qtd_pares = sum(1 for d in jogo if d % 2 == 0)
    qtd_impares = len(jogo) - qtd_pares

    while len(jogo) < 15:
        if qtd_pares < 7 and pares:
            d = pares.pop(0)
            jogo.append(d)
            qtd_pares += 1
        elif qtd_impares < 8 and impares:
            d = impares.pop(0)
            jogo.append(d)
            qtd_impares += 1
        else:
            break

    return sorted(jogo)

# ---------------------------
# Gerar jogos
# ---------------------------
def gerar_jogos(
    dezenas_base, qtd_15=0, dezenas_fixas=None, atrasadas=None
):
    jogos = []
    dezenas_fixas = dezenas_fixas or []
    atrasadas = atrasadas or []

    if len(dezenas_fixas) > 10:
        raise ValueError("As dezenas fixas devem ter no máximo 10 números.")

    # completar fixas automáticas (top base) até 10
    fixas_auto = []
    if len(dezenas_fixas) < 10:
        for d in dezenas_base:
            if d not in dezenas_fixas and len(dezenas_fixas) + len(fixas_auto) < 10:
                fixas_auto.append(d)

    # Função para criar jogo completo
    def criar_jogo():
        jogo = []
        origem = {}

        # fixas do usuário
        for d in dezenas_fixas:
            jogo.append(d)
            origem[d] = "fixa_usuario"

        # fixas automáticas
        for d in fixas_auto:
            jogo.append(d)
            origem[d] = "fixa_auto"

        # atrasadas
        for d in atrasadas:
            if d not in jogo:
                jogo.append(d)
                origem[d] = "atrasada"

        # completar com pares/ímpares equilibrados
        jogo = equilibrar_pares_impares(jogo, dezenas_base)
        for d in jogo:
            origem.setdefault(d, "base")

        return sorted(jogo), origem

    for _ in range(qtd_15):
        jogos.append(criar_jogo())

    return jogos
