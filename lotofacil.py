import pandas as pd
from collections import Counter

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
