"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Funções principais usadas no app “Lotofácil Inteligente”.
"""
"""
lotofacil.py
Funções de suporte para o app "Lotofácil Inteligente".

Principais responsabilidades:
- carregar dados CSV da Lotofácil
- cálculos estatísticos (frequência, atrasos, pares/ímpares, sequências)
- gerar jogos balanceados (respeitando tamanhos mistos)
- avaliar jogos contra o histórico (quantas vezes um jogo teve 11..15 acertos)
- gerar PDFs simples com os jogos
- salvar bolões/jogos gerados em CSV
- atualizar base via API da Caixa
"""

import os
import csv
import json
import uuid
import random
import base64
import requests
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from github import Github  # usado apenas na função atualizar_csv_github (se necessário)


# ---------------------------
# Carregar dados do CSV
# ---------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    """
    Lê o arquivo CSV da Lotofácil, mesmo com campos mistos (',' e ';').
    Faz detecção automática e normaliza os dados.
    """
    try:
        if not os.path.exists(file_path):
            print(f"⚠️ Arquivo {file_path} não encontrado.")
            return None

        # Lê algumas linhas brutas
        with open(file_path, "r", encoding="utf-8") as f:
            amostra = f.read(4096)

        # Detectar separador dominante (conta mais ocorrências)
        sep_comma = amostra.count(",")
        sep_semicolon = amostra.count(";")
        sep = "," if sep_comma >= sep_semicolon else ";"

        # Lê o arquivo usando o separador dominante
        df = pd.read_csv(file_path, sep=sep, engine="python", encoding="utf-8", on_bad_lines="skip", dtype=str)

        # Remove colunas totalmente vazias
        df = df.dropna(axis=1, how="all")
        df = df.dropna(how="all")

        # Corrige nomes se não houver "Bola1"
        if not any("Bola" in c for c in df.columns):
            # tenta identificar as 15 primeiras dezenas (entre 3ª e 17ª colunas)
            for i in range(1, 16):
                if f"Bola{i}" not in df.columns and i + 1 < len(df.columns):
                    df.rename(columns={df.columns[i + 1]: f"Bola{i}"}, inplace=True)

        print(f"✅ CSV carregado: {len(df)} concursos | separador '{sep}' detectado")
        return df

    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return None


# ---------------------------
# Estatísticas
# ---------------------------
def _colunas_dezenas(df):
    """Retorna lista de colunas que representam dezenas (contendo 'Bola' ou 'BolaX')."""
    cols = [c for c in df.columns if "Bola" in c or c.lower().startswith("bola")]
    # fallback: colunas entre 1..25 presentes como strings
    if not cols:
        cols = [c for c in df.columns if c.isdigit() and 1 <= int(c) <= 25]
    return cols


def calcular_frequencia(df, ultimos=None):
    """
    Conta quantas vezes cada dezena saiu.
    ultimos=None => usa todo o arquivo (padrão alterado para usar tudo)
    """
    dezenas_cols = _colunas_dezenas(df)
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
    dados = df.tail(ultimos)[dezenas_cols]
    # transforma em series numeric e conta
    valores = pd.Series(pd.to_numeric(dados.values.flatten(), errors="coerce"))
    valores_limpos = valores.dropna().astype(int)
    contagem = Counter(valores_limpos)
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    return ranking


def calcular_atrasos(df):
    """
    Calcula atraso atual e máximo para cada dezena (1..25).
    Retorna DataFrame com colunas ['Dezena','Máx Atraso','Atraso Atual'].
    """
    dezenas_cols = _colunas_dezenas(df)
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}
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
    dezenas_cols = _colunas_dezenas(df)
    resultados = []
    for _, row in df.iterrows():
        dezenas = pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int)
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = len(dezenas) - pares
        resultados.append((pares, impares))
    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")


def calcular_sequencias(df):
    dezenas_cols = _colunas_dezenas(df)
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
    dezenas_cols = _colunas_dezenas(df)
    combos = Counter()
    for _, row in df.iterrows():
        dezenas = sorted(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        combos.update(combinations(dezenas, 2))
    return pd.DataFrame(combos.most_common(20), columns=["Combinação", "Ocorrências"])


# ---------------------------
# Geração de jogos (respeitando tamanho)
# ---------------------------
def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho=15):
    """
    Gera 'qtd_jogos' jogos com exatamente 'tamanho' dezenas cada.
    Estratégia:
      - pega top frequentes (peso alto)
      - pega top atrasadas (peso médio)
      - completa aleatoriamente garantindo diversidade e tamanho exato
    Retorna lista de tuplas (jogo_sorted_list, origem_dict)
    """
    try:
        if tamanho < 15 or tamanho > 20:
            raise ValueError("tamanho deve estar entre 15 e 20")

        dezenas_cols = _colunas_dezenas(df)
        # ranking frequência (todo histórico)
        freq_df = calcular_frequencia(df, ultimos=len(df))
        top_freq = freq_df.head(12)["Dezena"].tolist() if not freq_df.empty else list(range(1, 26))

        # ranking atrasadas
        atrasos_df = calcular_atrasos(df)
        top_atraso = atrasos_df.sort_values("Atraso Atual", ascending=False)["Dezena"].head(10).tolist()

        jogos = []
        for _ in range(qtd_jogos):
            jogo = set()
            origem = {}

            # adicionar até 6 frequentes, mas sem ultrapassar tamanho
            qtd_freq = min(6, tamanho - 5)  # garante espaço para outras categorias
            for d in random.sample(top_freq, min(qtd_freq, len(top_freq))):
                jogo.add(int(d))
                origem[int(d)] = "frequente"

            # adicionar até 4 atrasadas
            qtd_atr = min(4, tamanho - len(jogo))
            for d in random.sample(top_atraso, min(qtd_atr, len(top_atraso))):
                if d not in jogo:
                    jogo.add(int(d))
                    origem[int(d)] = "atrasada"

            # completar com números aleatórios mantendo 1..25
            while len(jogo) < tamanho:
                d = random.randint(1, 25)
                if d not in jogo:
                    jogo.add(d)
                    origem[d] = origem.get(d, "aleatoria")

            jogo_final = sorted(jogo)[:tamanho]  # garantir tamanho exato
            # ajustar origem dict apenas para as dezenas do jogo_final
            origem_final = {d: origem.get(d, "aleatoria") for d in jogo_final}
            jogos.append((jogo_final, origem_final))

        return jogos
    except Exception as e:
        print("Erro gerar_jogos_balanceados:", e)
        return []


# ---------------------------
# Avaliação histórica (11..15 pts)
# ---------------------------
def avaliar_jogos_historico(df, jogos):
    """
    Para cada jogo (lista de dezenas), conta quantas vezes, no histórico,
    esse jogo obteve 11, 12, 13, 14 e 15 acertos.
    Retorna um DataFrame com colunas: ['Jogo','Dezenas','11 pts','12 pts','13 pts','14 pts','15 pts']
    """
    dezenas_cols = _colunas_dezenas(df)
    linhas = []
    # prepara lista de concursos como conjuntos (melhora performance)
    concursos = []
    for _, row in df.iterrows():
        sorteadas = set(pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int))
        concursos.append(sorteadas)

    for idx, (jogo, origem) in enumerate(jogos, start=1):
        cont = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        set_jogo = set(jogo)
        for sorteadas in concursos:
            acertos = len(set_jogo & sorteadas)
            if acertos >= 11:
                cont[acertos] += 1
        linhas.append({
            "Jogo": idx,
            "Dezenas": " ".join(f"{d:02d}" for d in sorted(jogo)),
            "11 pts": cont[11],
            "12 pts": cont[12],
            "13 pts": cont[13],
            "14 pts": cont[14],
            "15 pts": cont[15],
        })
    return pd.DataFrame(linhas)


# ---------------------------
# Valor da aposta
# ---------------------------
def calcular_valor_aposta(qtd_dezenas):
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)


# ---------------------------
# Gerar PDF simples com bolão
# ---------------------------
def gerar_pdf_jogos(jogos, nome="Bolão", participantes="", pix=""):
    participantes_lista = [p.strip() for p in participantes.split(",") if p.strip()]
    num_participantes = len(participantes_lista) if participantes_lista else 1
    valor_total = sum(calcular_valor_aposta(len(j)) for j, _ in jogos)
    valor_por_pessoa = valor_total / num_participantes if num_participantes else valor_total

    file_name = f"bolao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    largura, altura = A4
    y = altura - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, f"🎯 {nome}")
    y -= 1 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 0.8 * cm

    c.drawString(2 * cm, y, "Participantes:")
    y -= 0.5 * cm
    for p in participantes_lista:
        c.drawString(2.5 * cm, y, f"- {p}")
        y -= 0.4 * cm

    c.drawString(2 * cm, y, f"PIX: {pix if pix else '-'}")
    y -= 0.8 * cm

    c.drawString(2 * cm, y, f"Total de jogos: {len(jogos)}  |  Valor total: R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 0.8 * cm

    for i, (jogo, origem) in enumerate(jogos, start=1):
        if y < 3 * cm:
            c.showPage()
            y = altura - 2 * cm
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, y, f"Jogo {i} ({len(jogo)} dezenas): {' '.join(str(d).zfill(2) for d in jogo)}")
        y -= 0.6 * cm

    c.save()
    return file_name


# ---------------------------
# Salvar bolão completo (código para busca futura)
# ---------------------------
def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    """
    Atualiza (acrescenta) os jogos gerados no arquivo 'jogos_gerados.csv'
    sem apagar os jogos anteriores. Cada execução adiciona um novo registro.
    """

    # Gera um código único para cada bolão
    codigo = f"B{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Garante que o diretório exista
    pasta = os.path.dirname(file_path)
    if pasta and not os.path.exists(pasta):
        os.makedirs(pasta)

    # Constrói o registro (linha)
    dados = {
        "CodigoBolao": codigo,
        "DataHora": data_hora,
        "Participantes": participantes,
        "Pix": pix,
        "QtdJogos": len(jogos),
        "ValorTotal": round(valor_total, 2),
        "ValorPorPessoa": round(valor_por_pessoa, 2),
        "Jogos": json.dumps([sorted(list(j)) for j, _ in jogos]),
        "ConcursoBase": concurso_base or ""
    }

    # Se o arquivo existir, faz append; se não, cria com cabeçalho
    criar_cabecalho = not os.path.exists(file_path)

    # --- Detecta separador existente (para manter compatibilidade) ---
    separador = ","
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            primeira_linha = f.readline()
            if ";" in primeira_linha:
                separador = ";"

    # --- Escreve no arquivo ---
    with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=dados.keys(), delimiter=separador)
        if criar_cabecalho:
            writer.writeheader()
        writer.writerow(dados)

    return codigo


# ---------------------------
# Atualizar CSV via API Caixa (exemplo simplificado)
# ---------------------------
def atualizar_csv_github():
    """
    Função simplificada: baixa último concurso e adiciona ao Lotofacil.csv local.
    (Se tiver GH_TOKEN e quiser atualizar no GitHub, podemos estender.)
    """
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        r = requests.get(url, headers={"accept": "application/json"}, timeout=10)
        if r.status_code != 200:
            return "Erro ao acessar API da Caixa."
        d = r.json()
        numero = int(d["numero"])
        data = d["dataApuracao"]
        dezenas = [int(x) for x in d["listaDezenas"]]
        file_path = "Lotofacil.csv"
        # monta nova linha com ; como separador (compatível com carregamento)
        nova = [str(numero), data] + [str(x) for x in dezenas]
        if os.path.exists(file_path):
            # tenta detectar separador do arquivo existente
            with open(file_path, "r", encoding="utf-8") as f:
                linha0 = f.readline()
            sep = ";" if ";" in linha0 else ","
            with open(file_path, "a", encoding="utf-8", newline="") as f:
                f.write(sep.join(nova) + "\n")
        else:
            # cria com cabeçalho simples
            cols = ["Concurso", "Data"] + [f"Bola{i}" for i in range(1, 16)]
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(cols) + "\n")
                f.write(";".join(nova) + "\n")
        return f"Concurso {numero} adicionado localmente."
    except Exception as e:
        return f"Erro ao atualizar base: {e}"


# ---------------------------
# Último concurso via API
# ---------------------------
def obter_concurso_atual_api():
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return {"numero": d["numero"], "dataApuracao": d["dataApuracao"], "dezenas": [int(x) for x in d["listaDezenas"]]}
    except:
        pass
    return None

