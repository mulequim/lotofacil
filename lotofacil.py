"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Este módulo implementa todas as funções usadas no app “Lotofácil Inteligente”.
Ele reúne rotinas para análise estatística, geração de jogos, conferência e salvamento de bolões.

───────────────────────────────
🔹 Estrutura das funções
───────────────────────────────
1️⃣ Carregamento dos dados históricos
2️⃣ Cálculos estatísticos (frequência, atrasos, pares/ímpares, sequências, combinações)
3️⃣ Geração de jogos inteligentes
4️⃣ Salvamento e avaliação de bolões
5️⃣ Geração de PDFs
6️⃣ Atualização automática da base (API Caixa)
7️⃣ Consulta do último concurso
"""

# ------------------------------------------------------------
# 🧩 Importações
# ------------------------------------------------------------
import pandas as pd
import requests
import base64
import os
import random
import csv
import json
import uuid
from collections import Counter
from itertools import combinations
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime

# ------------------------------------------------------------
# 📂 1️⃣ CARREGAMENTO DOS DADOS
# ------------------------------------------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    """
    Lê o arquivo CSV com os resultados da Lotofácil.
    Detecta automaticamente o separador (',' ou ';') e remove linhas vazias.

    Retorna:
        pandas.DataFrame -> base de resultados
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            primeira = f.readline()
            sep = ";" if ";" in primeira else ","

        df = pd.read_csv(file_path, sep=sep, encoding="utf-8", dtype=str)
        df = df.dropna(how="all")
        return df
    except Exception as e:
        print("❌ Erro ao carregar dados:", e)
        return None

# ------------------------------------------------------------
# 📊 2️⃣ CÁLCULOS ESTATÍSTICOS
# ------------------------------------------------------------
def calcular_frequencia(df, ultimos=None):
    """
    Conta quantas vezes cada dezena foi sorteada.
    Pode considerar apenas os 'n' últimos concursos.
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)

    dados = df.tail(ultimos)[dezenas_cols]

    # 🔧 CORRIGIDO: converte explicitamente em Series antes de usar dropna()
    valores = pd.Series(pd.to_numeric(dados.values.flatten(), errors="coerce"))
    valores_limpos = valores.dropna().astype(int)

    contagem = Counter(valores_limpos)
    return pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])

def calcular_atrasos(df):
    """
    Calcula quantos concursos cada dezena está sem aparecer.
    Retorna também o maior atraso histórico.
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}

    for _, row in df[::-1].iterrows():
        dezenas = set(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        for d in range(1, 26):
            if d not in dezenas:
                atual_atraso[d] += 1
            else:
                max_atrasos[d] = max(max_atrasos[d], atual_atraso[d])
                atual_atraso[d] = 0

    dados = [[d, max_atrasos[d], atual_atraso[d]] for d in range(1, 26)]
    return pd.DataFrame(dados, columns=["Dezena", "Máx Atraso", "Atraso Atual"])

def calcular_pares_impares(df):
    """
    Conta quantas vezes ocorreu cada combinação de pares e ímpares.
    Exemplo: (8 pares, 7 ímpares) = 35 vezes.
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    resultados = []

    for _, row in df.iterrows():
        dezenas = pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int)
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = len(dezenas) - pares
        resultados.append((pares, impares))

    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")

def calcular_sequencias(df):
    """
    Conta quantas sequências consecutivas (como 10,11,12) ocorrem.
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    seqs = Counter()

    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        seq = 1
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i - 1] + 1:
                seq += 1
            else:
                if seq >= 2:
                    seqs[seq] += 1
                seq = 1
        if seq >= 2:
            seqs[seq] += 1

    return pd.DataFrame(seqs.items(), columns=["Tamanho Sequência", "Ocorrências"])

def analisar_combinacoes_repetidas(df):
    """
    Analisa combinações recorrentes de pares de dezenas.
    Exemplo: 01 e 02 saíram juntos 42 vezes.
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    combos = Counter()

    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        combos.update(combinations(dezenas, 2))

    mais = combos.most_common(10)
    return pd.DataFrame(mais, columns=["Combinação", "Ocorrências"])

# ------------------------------------------------------------
# 🎯 3️⃣ GERAÇÃO DE JOGOS
# ------------------------------------------------------------
def gerar_jogos_balanceados(df, qtd_jogos=5, tamanho=15):
    """
    Gera jogos equilibrados misturando dezenas frequentes, atrasadas e neutras.
    """
    try:
        dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
        jogos = []

        for _ in range(qtd_jogos):
            linha = df.sample(1).iloc[0]
            dezenas = pd.to_numeric(linha[dezenas_cols], errors="coerce").dropna().astype(int).tolist()
            dezenas = [d for d in dezenas if 1 <= d <= 25]

            if len(dezenas) > tamanho:
                dezenas = random.sample(dezenas, tamanho)
            elif len(dezenas) < tamanho:
                faltantes = random.sample([d for d in range(1, 26) if d not in dezenas], tamanho - len(dezenas))
                dezenas.extend(faltantes)

            origem = {d: "equilibrio" for d in dezenas}
            jogos.append((sorted(dezenas), origem))
        return jogos
    except Exception as e:
        print("❌ Erro gerar_jogos_balanceados:", e)
        return []

# ------------------------------------------------------------
# 💾 4️⃣ SALVAR E AVALIAR JOGOS / BOLÕES
# ------------------------------------------------------------
def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    """
    Salva o bolão no CSV com código único (B+data+UUID).
    """
    codigo = f"B{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    dados = {
        "CodigoBolao": codigo,
        "DataHora": data_hora,
        "Participantes": participantes,
        "Pix": pix,
        "QtdJogos": len(jogos),
        "ValorTotal": round(valor_total, 2),
        "ValorPorPessoa": round(valor_por_pessoa, 2),
        "Jogos": json.dumps([j for j, _ in jogos]),
        "ConcursoBase": concurso_base or ""
    }

    try:
        criar_cabecalho = not os.path.exists(file_path)
        with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=dados.keys())
            if criar_cabecalho:
                writer.writeheader()
            writer.writerow(dados)
        return codigo
    except Exception as e:
        print("Erro ao salvar bolão:", e)
        return None

def avaliar_jogos(jogos, dezenas_sorteadas):
    """
    Avalia quantos acertos cada jogo teve comparando com o resultado sorteado.
    Retorna um DataFrame com as colunas: ["Jogo", "Acertos"].
    """
    resultados = []
    for idx, jogo in enumerate(jogos, start=1):
        acertos = len(set(jogo) & set(dezenas_sorteadas))
        resultados.append({"Jogo": idx, "Acertos": acertos})
    return pd.DataFrame(resultados)

# ------------------------------------------------------------
# 🧾 5️⃣ PDF E VALORES
# ------------------------------------------------------------
def calcular_valor_aposta(qtd_dezenas):
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)

def gerar_pdf_jogos(jogos, nome="Bolão", participantes="", pix=""):
    """
    Cria um PDF contendo:
      - Lista dos jogos
      - Participantes
      - Chave PIX
    """
    participantes_lista = [p.strip() for p in participantes.split(",") if p.strip()]
    num_participantes = len(participantes_lista) if participantes_lista else 1

    valor_total = sum(calcular_valor_aposta(len(j)) for j, _ in jogos)
    valor_por_pessoa = valor_total / num_participantes

    file_name = f"bolao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    largura, altura = A4
    y = altura - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, f"🎯 {nome}")
    y -= 1 * cm

    for i, (jogo, _) in enumerate(jogos, 1):
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, y, f"Jogo {i}: {' '.join(str(x).zfill(2) for x in jogo)}")
        y -= 0.6 * cm
        if y < 3 * cm:
            c.showPage()
            y = altura - 2 * cm

    c.save()
    return file_name

# ------------------------------------------------------------
# 🔄 6️⃣ ATUALIZAÇÃO AUTOMÁTICA DA BASE
# ------------------------------------------------------------
def atualizar_csv_github():
    """
    Atualiza o arquivo Lotofacil.csv com o último concurso via API oficial.
    """
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        r = requests.get(url, headers={"accept": "application/json"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            dezenas = d["listaDezenas"]
            numero = d["numero"]
            data = d["dataApuracao"]

            if os.path.exists("Lotofacil.csv"):
                df = pd.read_csv("Lotofacil.csv", sep=";", encoding="utf-8")
                if str(numero) in df["Concurso"].astype(str).values:
                    return f"✅ Concurso {numero} já atualizado."

            nova = {"Concurso": numero, "Data": data}
            for i, dez in enumerate(dezenas, 1):
                nova[f"Bola{i}"] = dez

            if os.path.exists("Lotofacil.csv"):
                df = pd.read_csv("Lotofacil.csv", sep=";", encoding="utf-8")
                df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)
            else:
                cols = ["Concurso"] + [f"Bola{i}" for i in range(1, 16)] + ["Data"]
                df = pd.DataFrame([nova], columns=cols)

            df.to_csv("Lotofacil.csv", sep=";", index=False, encoding="utf-8")
            return f"✅ Base atualizada com o concurso {numero}."
        else:
            return "⚠️ Erro ao acessar API da Caixa."
    except Exception as e:
        return f"❌ Erro ao atualizar: {e}"

# ------------------------------------------------------------
# 🌐 7️⃣ CONSULTA ÚLTIMO CONCURSO
# ------------------------------------------------------------
def obter_concurso_atual_api():
    """
    Retorna o último concurso da Lotofácil com número, data e dezenas.
    """
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return {"numero": d["numero"], "dataApuracao": d["dataApuracao"], "dezenas": [int(x) for x in d["listaDezenas"]]}
    except:
        pass
    return None
