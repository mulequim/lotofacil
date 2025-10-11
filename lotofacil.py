"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Funções principais usadas no app “Lotofácil Inteligente”.
"""

import pandas as pd
import requests
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
# 🧩 1️⃣ Carregar dados
# ------------------------------------------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    try:
        sep = ";" if ";" in open(file_path, "r", encoding="utf-8").readline() else ","
        df = pd.read_csv(file_path, sep=sep, encoding="utf-8", dtype=str).dropna(how="all")
        return df
    except Exception as e:
        print("❌ Erro carregar_dados:", e)
        return None

# ------------------------------------------------------------
# 📊 2️⃣ Estatísticas
# ------------------------------------------------------------
def calcular_frequencia(df, ultimos=None):
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
    dados = df.tail(ultimos)[dezenas_cols]
    valores = pd.Series(pd.to_numeric(dados.values.flatten(), errors="coerce")).dropna().astype(int)
    contagem = Counter(valores)
    return pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])

def calcular_atrasos(df):
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    max_atrasos, atual_atraso = {d: 0 for d in range(1, 26)}, {d: 0 for d in range(1, 26)}
    for _, row in df[::-1].iterrows():
        dezenas = set(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        for d in range(1, 26):
            if d not in dezenas:
                atual_atraso[d] += 1
            else:
                max_atrasos[d] = max(max_atrasos[d], atual_atraso[d])
                atual_atraso[d] = 0
    return pd.DataFrame([[d, max_atrasos[d], atual_atraso[d]] for d in range(1, 26)],
                        columns=["Dezena", "Máx Atraso", "Atraso Atual"])

def calcular_pares_impares(df):
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    resultados = []
    for _, row in df.iterrows():
        dezenas = pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int)
        pares = sum(d % 2 == 0 for d in dezenas)
        resultados.append((pares, len(dezenas) - pares))
    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")

def calcular_sequencias(df):
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
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    combos = Counter()
    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        combos.update(combinations(dezenas, 2))
    return pd.DataFrame(combos.most_common(10), columns=["Combinação", "Ocorrências"])

# ------------------------------------------------------------
# 🎯 3️⃣ Geração de Jogos Balanceados (agora aceita tamanhos variados)
# ------------------------------------------------------------
def gerar_jogos_balanceados(df, qtd_jogos=5, tamanhos=[15]):
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    jogos = []
    for i in range(qtd_jogos):
        tamanho = random.choice(tamanhos) if isinstance(tamanhos, list) else tamanhos
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

# ------------------------------------------------------------
# 🧮 4️⃣ Avaliar jogos com histórico (novo)
# ------------------------------------------------------------
def avaliar_jogos_historico(df, jogos):
    dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
    resultados = []
    for idx, (jogo, _) in enumerate(jogos, 1):
        acertos_hist = []
        for _, row in df.iterrows():
            dezenas_sorteadas = pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int)
            acertos = len(set(jogo) & set(dezenas_sorteadas))
            acertos_hist.append(acertos)
        contagem = Counter(acertos_hist)
        resultados.append({
            "Jogo": idx,
            "Tamanho": len(jogo),
            "15": contagem.get(15, 0),
            "14": contagem.get(14, 0),
            "13": contagem.get(13, 0),
            "12": contagem.get(12, 0),
            "11": contagem.get(11, 0)
        })
    return pd.DataFrame(resultados)

# ------------------------------------------------------------
# 💾 5️⃣ Salvar bolão / PDF / API
# ------------------------------------------------------------
def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    codigo = f"B{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    dados = {
        "CodigoBolao": codigo,
        "DataHora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Participantes": participantes,
        "Pix": pix,
        "QtdJogos": len(jogos),
        "ValorTotal": round(valor_total, 2),
        "ValorPorPessoa": round(valor_por_pessoa, 2),
        "Jogos": json.dumps([j for j, _ in jogos]),
        "ConcursoBase": concurso_base or ""
    }
    criar = not os.path.exists(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dados.keys())
        if criar: w.writeheader()
        w.writerow(dados)
    return codigo

def calcular_valor_aposta(qtd): return {15:3.5,16:56,17:476,18:2856,19:13566,20:54264}.get(qtd,0)

def gerar_pdf_jogos(jogos, nome="Bolão", participantes="", pix=""):
    file_name = f"bolao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    largura, altura = A4; y = altura - 2*cm
    c.setFont("Helvetica-Bold",14); c.drawString(2*cm,y,f"{nome}"); y-=1*cm
    for i,(jogo,_) in enumerate(jogos,1):
        c.setFont("Helvetica",11); c.drawString(2*cm,y,f"Jogo {i}: {' '.join(str(x).zfill(2) for x in jogo)}")
        y-=0.6*cm
        if y<3*cm: c.showPage(); y=altura-2*cm
    c.save(); return file_name

def atualizar_csv_github():
    try:
        url="https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        r=requests.get(url,headers={"accept":"application/json"},timeout=10)
        if r.status_code!=200: return "⚠️ Erro API Caixa."
        d=r.json(); dezenas=d["listaDezenas"]; numero=d["numero"]; data=d["dataApuracao"]
        if os.path.exists("Lotofacil.csv"):
            df=pd.read_csv("Lotofacil.csv",sep=";",encoding="utf-8")
            if str(numero) in df["Concurso"].astype(str).values:
                return f"✅ Concurso {numero} já atualizado."
        nova={"Concurso":numero,"Data":data}
        for i,dez in enumerate(dezenas,1): nova[f"Bola{i}"]=dez
        if os.path.exists("Lotofacil.csv"):
            df=pd.read_csv("Lotofacil.csv",sep=";",encoding="utf-8")
            df=pd.concat([df,pd.DataFrame([nova])],ignore_index=True)
        else:
            cols=["Concurso"]+[f"Bola{i}" for i in range(1,16)]+["Data"]
            df=pd.DataFrame([nova],columns=cols)
        df.to_csv("Lotofacil.csv",sep=";",index=False,encoding="utf-8")
        return f"✅ Base atualizada com o concurso {numero}."
    except Exception as e: return f"❌ Erro: {e}"

def obter_concurso_atual_api():
    try:
        r=requests.get("https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",timeout=10)
        if r.status_code==200:
            d=r.json()
            return {"numero":d["numero"],"dataApuracao":d["dataApuracao"],"dezenas":[int(x) for x in d["listaDezenas"]]}
    except: pass
    return None
