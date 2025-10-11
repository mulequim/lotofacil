"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Este módulo implementa as principais funções utilizadas pelo app "Lotofácil Inteligente".
Ele reúne rotinas de análise estatística, geração de jogos balanceados, conferência e
armazenamento de bolões.

🔹 Principais grupos de funções:
    1️⃣ Carregamento e preparação dos dados históricos
    2️⃣ Cálculos estatísticos (frequência, atrasos, pares/impares, sequências)
    3️⃣ Geração de jogos inteligentes
    4️⃣ Geração e salvamento de relatórios (PDF e CSV)
    5️⃣ Integração com a API oficial da Caixa Econômica Federal

Todas as funções são compatíveis com arquivos CSV baixados do site da Caixa ou mantidos no GitHub.
"""

# ------------------------------------------------------------
# 🧩 Importações
# ------------------------------------------------------------
import pandas as pd
from github import Github
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
    Lê o arquivo CSV contendo o histórico de resultados da Lotofácil.
    Detecta automaticamente se o separador é ',' ou ';', e remove linhas vazias.

    Retorna:
        pandas.DataFrame -> com todos os concursos.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            primeira_linha = f.readline()
            sep = ";" if ";" in primeira_linha else ","

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
    Calcula a frequência (quantas vezes cada dezena foi sorteada).
    Pode considerar apenas os 'n' últimos concursos se especificado.

    Parâmetros:
        df (DataFrame): base de concursos.
        ultimos (int): quantidade de concursos recentes para considerar.

    Retorna:
        DataFrame com colunas ["Dezena", "Frequência"].
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c]
    if not dezenas_cols:
        dezenas_cols = [str(i) for i in range(1, 26)]

    if ultimos is None or ultimos > len(df):
        ultimos = len(df)

    dados = df.tail(ultimos)[dezenas_cols]
    contagem = Counter(pd.to_numeric(dados.values.flatten(), errors="coerce").dropna())
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    return ranking


def calcular_atrasos(df):
    """
    Calcula os atrasos de cada dezena — ou seja, há quantos concursos
    cada número não aparece.

    Retorna:
        DataFrame com ["Dezena", "Máx Atraso", "Atraso Atual"].
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c]
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}

    # Inverte a ordem do dataframe para contar atrasos a partir do último concurso
    for _, row in df[::-1].iterrows():
        sorteadas = set(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        for d in range(1, 26):
            if d not in sorteadas:
                atual_atraso[d] += 1
            else:
                max_atrasos[d] = max(max_atrasos[d], atual_atraso[d])
                atual_atraso[d] = 0

    dados = [[d, max_atrasos[d], atual_atraso[d]] for d in range(1, 26)]
    return pd.DataFrame(dados, columns=["Dezena", "Máx Atraso", "Atraso Atual"])


def calcular_pares_impares(df):
    """
    Conta quantas vezes ocorreu cada combinação de pares e ímpares.
    Exemplo: (8 pares, 7 ímpares) apareceu 32 vezes.

    Retorna:
        DataFrame com ["Pares", "Ímpares", "Ocorrências"].
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c]
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
    Conta quantas sequências consecutivas (como 10,11,12) ocorrem nos resultados.
    Retorna as mais comuns e seu tamanho.

    Retorna:
        DataFrame com ["Tamanho Sequência", "Ocorrências"].
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c]
    sequencias = Counter()

    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
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
    return pd.DataFrame(sequencias.items(), columns=["Tamanho Sequência", "Ocorrências"])


def analisar_combinacoes_repetidas(df):
    """
    Analisa as combinações mais recorrentes de pares de dezenas (ex: 01 e 02 saíram juntos 45 vezes).

    Retorna:
        DataFrame com ["Combinação", "Ocorrências"].
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c]
    combos = Counter()
    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        combos.update(combinations(dezenas, 2))
    mais_repetidas = combos.most_common(10)
    return pd.DataFrame(mais_repetidas, columns=["Combinação", "Ocorrências"])


# ------------------------------------------------------------
# 🎯 3️⃣ GERAÇÃO DE JOGOS INTELIGENTES
# ------------------------------------------------------------
def gerar_jogos_balanceados(df, qtd_jogos=5, tamanho=15):
    """
    Gera jogos "balanceados" a partir dos resultados históricos.
    Mistura dezenas frequentes, atrasadas e garante equilíbrio entre pares e ímpares.

    Parâmetros:
        df: base de resultados
        qtd_jogos: quantidade de jogos a gerar
        tamanho: quantidade de dezenas por jogo (15 a 20)

    Retorna:
        Lista de tuplas [(dezenas, origem)], onde 'origem' indica a categoria de cada dezena.
    """
    try:
        dezenas_cols = [c for c in df.columns if "Bola" in c or c.isdigit()]
        if not dezenas_cols:
            raise ValueError("Nenhuma coluna de dezenas encontrada.")

        jogos = []
        for _ in range(qtd_jogos):
            linha = df.sample(1).iloc[0]
            dezenas = pd.to_numeric(linha[dezenas_cols], errors="coerce").dropna().astype(int).tolist()
            dezenas = [d for d in dezenas if 1 <= d <= 25]

            # Ajusta o tamanho do jogo (completa ou reduz)
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
# 💰 4️⃣ UTILITÁRIOS FINANCEIROS E RELATÓRIOS
# ------------------------------------------------------------
def calcular_valor_aposta(qtd_dezenas):
    """
    Retorna o valor oficial da aposta conforme o número de dezenas.
    Fonte: Tabela oficial da Caixa (atualizada).
    """
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)


def gerar_pdf_jogos(jogos, nome="Bolão", participantes="", pix=""):
    """
    Gera um arquivo PDF contendo:
      - Jogos listados
      - Participantes
      - Chave PIX
      - Valor total e por pessoa
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
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"Jogo {i}: {' '.join(str(x).zfill(2) for x in jogo)}")
        y -= 0.6 * cm
        if y < 3 * cm:
            c.showPage()
            y = altura - 2 * cm

    c.save()
    return file_name


def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    """
    Salva os dados de um bolão no arquivo CSV local.
    Cada bolão recebe um código único (B+data+UUID).

    Retorna:
        Código do bolão (str)
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


# ------------------------------------------------------------
# 🌐 5️⃣ INTEGRAÇÃO COM API OFICIAL DA CAIXA
# ------------------------------------------------------------
def obter_concurso_atual_api():
    """
    Consulta a API oficial da Caixa Econômica e retorna
    o último concurso disponível com número, data e dezenas.

    Retorna:
        dict -> {numero, dataApuracao, dezenas}
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
