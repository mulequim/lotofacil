import pandas as pd
from github import Github
import requests
import base64
import os
import random
from collections import Counter
from itertools import combinations
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime


# ---------------------------
# Carregar dados do CSV
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
def calcular_frequencia(df, ultimos=None):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
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

    dados = [[d, max_atrasos[d], atual_atraso[d]] for d in range(1, 26)]
    return pd.DataFrame(dados, columns=["Dezena", "Máx Atraso", "Atraso Atual"])


# ---------------------------
# Pares e Ímpares
# ---------------------------
def calcular_pares_impares(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    resultados = []

    for _, row in df.iterrows():
        dezenas = row[dezenas_cols].values
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = 15 - pares
        resultados.append((pares, impares))

    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")


# ---------------------------
# Sequências
# ---------------------------
def calcular_sequencias(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    sequencias = Counter()

    for _, row in df.iterrows():
        dezenas = sorted(row[dezenas_cols].values)
        seq = 1
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i - 1] + 1:
                seq += 1
            else:
                if seq >= 2:
                    sequencias[seq] += 1
                seq = 1
        if seq >= 2:
            sequencias[seq] += 1

    df_seq = pd.DataFrame(sequencias.items(), columns=["Tamanho Sequência", "Ocorrências"])
    return df_seq.sort_values("Tamanho Sequência")


# ---------------------------
# Combinações mais recorrentes
# ---------------------------
def analisar_combinacoes_repetidas(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    combos_contagem = {"Pares": Counter(), "Trios": Counter(), "Quartetos": Counter()}

    for _, row in df.iterrows():
        dezenas = sorted(map(int, row[dezenas_cols].values))
        combos_contagem["Pares"].update(combinations(dezenas, 2))
        combos_contagem["Trios"].update(combinations(dezenas, 3))
        combos_contagem["Quartetos"].update(combinations(dezenas, 4))

    resultado = []
    for tipo, contagem in combos_contagem.items():
        for combo, freq in contagem.most_common(5):
            resultado.append({"Tipo": tipo, "Combinação": combo, "Ocorrências": freq})

    return pd.DataFrame(resultado)


# ---------------------------
# Gerar jogos balanceados
# ---------------------------
def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho_jogo=15):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]

    # Frequentes
    freq = calcular_frequencia(df)
    top_frequentes = freq.head(10)["Dezena"].tolist()

    # Atrasadas
    atrasos = calcular_atrasos(df)
    top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(5)["Dezena"].tolist()

    # Combinações mais comuns
    todas_combs = Counter()
    for _, row in df.iterrows():
        dezenas = sorted(row[dezenas_cols].values)
        for comb in combinations(dezenas, 3):
            todas_combs[comb] += 1
    trios_flat = list(set([n for trio, _ in todas_combs.most_common(5) for n in trio]))

    pares = [d for d in range(1, 26) if d % 2 == 0]
    impares = [d for d in range(1, 26) if d % 2 != 0]

    jogos = []
    for _ in range(qtd_jogos):
        jogo = set()
        origem = {}

        # Frequentes
        for d in random.sample(top_frequentes, min(6, len(top_frequentes))):
            jogo.add(d)
            origem[d] = "frequente"

        # Atrasadas
        for d in random.sample(top_atrasadas, min(3, len(top_atrasadas))):
            if d not in jogo:
                jogo.add(d)
                origem[d] = "atrasada"

        # Recorrentes
        for d in random.sample(trios_flat, min(3, len(trios_flat))):
            if d not in jogo:
                jogo.add(d)
                origem[d] = "repetida"

        # Completar
        while len(jogo) < tamanho_jogo:
            grupo = pares if len([x for x in jogo if x % 2 != 0]) > 7 else impares
            d = random.choice(grupo)
            if d not in jogo:
                jogo.add(d)
                origem[d] = "equilibrio"

        jogos.append((sorted(jogo), origem))

    return jogos


# ---------------------------
# Avaliar jogos
# ---------------------------
def avaliar_jogos(jogos, df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    resultados = []

    for idx, (jogo, origem) in enumerate(jogos, start=1):
        contagens = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        for _, row in df.iterrows():
            acertos = len(set(row[dezenas_cols].values) & set(jogo))
            if acertos >= 11:
                contagens[acertos] += 1
        resultados.append((idx, jogo, contagens))

    return resultados


# ---------------------------
# Valor da aposta
# ---------------------------
def calcular_valor_aposta(qtd_dezenas):
    precos = {
        15: 3.50,
        16: 56.00,
        17: 476.00,
        18: 2856.00,
        19: 13566.00,
        20: 54264.00
    }
    return precos.get(qtd_dezenas, 0)


# ---------------------------
# Geração de PDF
# ---------------------------
def gerar_pdf_jogos(jogos, nome="Loteria", participantes="", rateio="", pix=""):
    file_name = f"jogos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    largura, altura = A4
    y = altura - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, f"📄 Bolão Lotofácil - {nome}")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 0.8 * cm

    c.drawString(2 * cm, y, f"Participantes: {participantes}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Rateio: {rateio}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"PIX: {pix}")
    y -= 1 * cm

    for i, (jogo, origem) in enumerate(jogos, start=1):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"🎯 Jogo {i} ({len(jogo)} dezenas)")
        y -= 0.6 * cm
        c.setFont("Helvetica", 11)
        dezenas_str = "  ".join([str(d).zfill(2) for d in jogo])
        c.drawString(2.5 * cm, y, dezenas_str)
        y -= 0.6 * cm

        valor = calcular_valor_aposta(len(jogo))
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(2.5 * cm, y, f"💰 Valor: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 1 * cm

        if y < 4 * cm:
            c.showPage()
            y = altura - 3 * cm

    c.save()
    return file_name


# ---------------------------
# Último concurso da Caixa
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
        return None
    except Exception:
        return None


# ---------------------------
# Atualizar CSV no GitHub
# ---------------------------
def atualizar_csv_github():
    try:
        url_api = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        response = requests.get(url_api, headers={"accept": "application/json"}, timeout=10)
        if response.status_code != 200:
            return "❌ Erro ao acessar API da Caixa."

        data = response.json()
        numero = int(data["numero"])
        data_apuracao = data["dataApuracao"]
        dezenas = [int(d) for d in data["listaDezenas"]]

        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ Token do GitHub não encontrado. Configure o segredo GH_TOKEN."

        g = Github(token)
        repo = g.get_repo("mulequim/lotofacil")
        file_path = "Lotofacil.csv"
        contents = repo.get_contents(file_path)

        csv_data = base64.b64decode(contents.content).decode("utf-8").strip().split("\n")
        linhas = [l.split(",") for l in csv_data]
        ultimo_numero = int(linhas[-1][0])

        if numero <= ultimo_numero:
            return f"✅ Base já está atualizada (concurso {numero})."

        nova_linha = [str(numero), data_apuracao] + [str(d) for d in dezenas]
        linhas.append(nova_linha)
        novo_csv = "\n".join([",".join(l) for l in linhas])

        repo.update_file(
            path=file_path,
            message=f"Atualiza com o concurso {numero}",
            content=novo_csv,
            sha=contents.sha,
            branch="main"
        )

        return f"🎉 Concurso {numero} adicionado com sucesso e enviado ao GitHub!"
    except Exception as e:
        return f"❌ Erro ao atualizar GitHub: {e}"
