import pandas as pd
import random
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="🔄 %(message)s")


# ----------------------------
# 📌 Carregar dados
# ----------------------------
def carregar_dados(file_path):
    try:
        df = pd.read_csv(file_path, sep=",", encoding="latin1")
        df = df.dropna(how="all")
        dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
        for col in dezenas_cols:
            if col not in df.columns:
                logging.error(f"❌ Coluna {col} não encontrada no arquivo CSV.")
                return None
        logging.info(f"✅ Arquivo carregado com {len(df)} concursos")
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar {file_path}: {e}")
        return None


# ----------------------------
# 📌 Selecionar dezenas mais frequentes
# ----------------------------
def selecionar_dezenas(df, qtd=18, ultimos=50):
    if df is None or df.empty:
        return [], pd.Series()

    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    df_ultimos = df.tail(ultimos)
    todas_dezenas = df_ultimos[dezenas_cols].stack()
    frequencia = todas_dezenas.value_counts()
    return frequencia.head(qtd).index.tolist(), frequencia


# ----------------------------
# 📌 Calcular atrasos
# ----------------------------
def calcular_atrasos(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    atrasos = {d: 0 for d in range(1, 26)}
    max_atrasos = {d: 0 for d in range(1, 26)}
    contadores = {d: 0 for d in range(1, 26)}

    for _, row in df.iterrows():
        sorteadas = set(row[dezenas_cols])
        for d in range(1, 26):
            if d in sorteadas:
                if contadores[d] > max_atrasos[d]:
                    max_atrasos[d] = contadores[d]
                contadores[d] = 0
            else:
                contadores[d] += 1
                atrasos[d] = contadores[d]
    return atrasos, max_atrasos


# ----------------------------
# 📌 Gerar jogos inteligentes
# ----------------------------
def gerar_jogos(
    df,
    dezenas_base,
    qtd_15=0, qtd_16=0, qtd_17=0, qtd_18=0,
    dezenas_fixas=None,
    usar_fixas=True,
    mesclar_fixas=False,
    equilibrar_pares=False,
    usar_atrasadas=False,
    randomico=False
):
    jogos = []
    todas_dezenas = list(range(1, 26))

    # 🔹 Ajuste das dezenas fixas
    top_frequentes, freq = selecionar_dezenas(df, qtd=25, ultimos=200)
    if dezenas_fixas is None or len(dezenas_fixas) == 0:
        dezenas_fixas = top_frequentes[:11]
    elif len(dezenas_fixas) < 11:
        # completa até 11
        for d in top_frequentes:
            if d not in dezenas_fixas:
                dezenas_fixas.append(d)
            if len(dezenas_fixas) == 11:
                break
    else:
        dezenas_fixas = dezenas_fixas[:11]

    # 🔹 Cálculo dos atrasos
    atrasos, max_atrasos = calcular_atrasos(df)
    mais_atrasadas = sorted(atrasos, key=atrasos.get, reverse=True)[:10]

    def criar_jogo(tamanho):
        jogo = set()
        if usar_fixas:
            jogo.update(dezenas_fixas)
        elif mesclar_fixas:
            jogo.update(random.sample(dezenas_fixas, k=min(7, len(dezenas_fixas))))

        while len(jogo) < tamanho:
            candidatos = dezenas_base.copy()

            if usar_atrasadas:
                candidatos.extend(mais_atrasadas)

            if equilibrar_pares:
                pares = [n for n in todas_dezenas if n % 2 == 0]
                impares = [n for n in todas_dezenas if n % 2 != 0]
                if sum(1 for n in jogo if n % 2 == 0) < tamanho // 2:
                    candidatos.extend(pares)
                else:
                    candidatos.extend(impares)

            if randomico:
                n = random.randint(1, 25)
            else:
                n = random.choice(candidatos)

            jogo.add(n)
        return sorted(jogo)

    # 🔹 Gerar jogos nas quantidades pedidas
    for _ in range(qtd_15):
        jogos.append(criar_jogo(15))
    for _ in range(qtd_16):
        jogos.append(criar_jogo(16))
    for _ in range(qtd_17):
        jogos.append(criar_jogo(17))
    for _ in range(qtd_18):
        jogos.append(criar_jogo(18))

    return jogos


# ----------------------------
# 📌 Avaliar jogos contra histórico
# ----------------------------
def avaliar_jogos(jogos, df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    historico_sets = [set(row) for row in df[dezenas_cols].values]
    resultados_finais = []

    for idx, jogo in enumerate(jogos, 1):
        jogo_set = set(jogo)
        contagens = defaultdict(int)
        for concurso_set in historico_sets:
            acertos = len(jogo_set.intersection(concurso_set))
            if acertos >= 11:
                contagens[acertos] += 1
        resultados_finais.append((idx, jogo, dict(contagens)))
    return resultados_finais
