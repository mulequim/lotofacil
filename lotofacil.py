"""
Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Contém todas as funções de cálculo, estatística, geração de jogos e serviços
necessárias para o app "Lotofácil Inteligente".
Utiliza a nova base de dados Lotofacil_Concursos.csv como padrão.
"""

import re
import os
import csv
import json
import uuid
import random
import base64
import requests
import pandas as pd
import numpy as np
from collections import defaultdict
from collections import Counter
from itertools import combinations
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
# from github import Github  # Depende do ambiente

# ---------------------------
# Carregar dados do CSV e Limpeza
# ---------------------------

def carregar_dados(file_path="Lotofacil_Concursos.csv"):
    """
    Lê o arquivo CSV, detecta separador, e aplica pré-limpeza bruta
    nas colunas de dezenas para remover ruído antes do cálculo.
    """
    try:
        # --- 1. Carregamento ---
        if not os.path.exists(file_path):
            print(f"⚠️ Arquivo {file_path} não encontrado.")
            return None
        
        # Assume o separador vírgula, comum em CSVs da Caixa/Web
        sep = "," 
        df = pd.read_csv(file_path, sep=sep, engine="python", encoding="utf-8", on_bad_lines="skip", dtype=str)
        df = df.dropna(axis=1, how="all").dropna(how="all")
        
        # --- 2. Identificação das colunas 2 a 16 ---
        all_cols = list(df.columns)
        
        # Assume que as dezenas começam na 3ª coluna (índice 2)
        if len(all_cols) < 17:
             dezenas_cols = all_cols[2:]
        else:
             dezenas_cols = all_cols[2:17]

        # --- 3. Limpeza Bruta (Remove tudo que não é dígito ou NaN) ---
        for col in dezenas_cols:
            if col in df.columns:
                # Remove todos os caracteres que não são dígitos (0-9)
                df[col] = df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
        
        return df

    except Exception as e:
        print(f"❌ Erro ao carregar/limpar dados: {e}")
        return None

# ---------------------------
# Funções de Suporte à Estatística
# ---------------------------

def _colunas_dezenas(df):
    """Retorna lista estrita das colunas de dezenas (índice 2 a 16)."""
    all_cols = list(df.columns)
    if len(all_cols) < 17:
        return []
    return all_cols[2:17]


def calcular_atrasos(df):
    """
    Calcula o atraso atual e o atraso máximo de cada dezena (1..25)
    em um único passo.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])

    try:
        all_cols = list(df.columns)
        if len(all_cols) < 17:
             raise ValueError("DF não tem 17 colunas mínimas para dezenas.")
        dezenas_cols = all_cols[2:17]

        # 1. EXTRAÇÃO: Converte em número e filtra o domínio (1 a 25)
        df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
        df_dezenas = df_dezenas.mask((df_dezenas < 1) | (df_dezenas > 25))

        concursos = []
        for _, row in df_dezenas.iterrows():
            dezenas_finais = row.dropna().astype(int).tolist()
            concursos.append(set(dezenas_finais))

        if not concursos:
            raise ValueError("Nenhuma dezena pôde ser extraída após conversão.")

        # 2. Calcula em um único passo (Máx Atraso e Atraso Atual)
        max_atraso = {d: 0 for d in range(1, 26)}
        contador = {d: 0 for d in range(1, 26)}

        for sorteadas in concursos:
            for d in range(1, 26):
                if d in sorteadas:
                    max_atraso[d] = max(max_atraso[d], contador[d])
                    contador[d] = 0
                else:
                    contador[d] += 1

        # 3. Finaliza: O contador é o Atraso Atual
        atraso_atual = contador
        for d in range(1, 26):
             max_atraso[d] = max(max_atraso[d], atraso_atual[d])

        df_out = pd.DataFrame(
            [[d, max_atraso[d], atraso_atual[d]] for d in range(1, 26)],
            columns=["Dezena", "Máx Atraso", "Atraso Atual"]
        )

        return df_out.sort_values("Atraso Atual", ascending=False).reset_index(drop=True)

    except Exception as e:
        print(f"❌ Erro em calcular_atrasos: {e}")
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])


def calcular_frequencia(df, ultimos=None):
    """Conta quantas vezes cada dezena saiu no período especificado."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Dezena", "Frequência"])
        
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
        
    dados = df.tail(ultimos)[dezenas_cols]
    valores = pd.to_numeric(dados.values.flatten(), errors="coerce")
    valores_limpos = pd.Series(valores).dropna().astype(int)
    
    contagem = Counter(valores_limpos)
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    
    todas_dezenas = pd.DataFrame({"Dezena": range(1, 26)})
    ranking = todas_dezenas.merge(ranking, on="Dezena", how="left").fillna(0)
    
    return ranking.sort_values("Frequência", ascending=False).reset_index(drop=True)


def calcular_pares_impares(df):
    """Calcula a frequência das combinações de Pares/Ímpares."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Pares", "Ímpares", "Ocorrências"])
        
    df_dezenas = df[_colunas_dezenas(df)].apply(pd.to_numeric, errors='coerce')
    
    resultados = []
    for _, row in df_dezenas.iterrows():
        dezenas = row.dropna().astype(int)
        dezenas = dezenas[(dezenas >= 1) & (dezenas <= 25)] 
        
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = len(dezenas) - pares
        
        if len(dezenas) == 15:
             resultados.append((pares, impares))
             
    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")


def calcular_sequencias(df):
    """Calcula a frequência dos tamanhos de sequências (2 ou mais números consecutivos)."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Tamanho Sequência", "Ocorrências"])
        
    df_dezenas = df[_colunas_dezenas(df)].apply(pd.to_numeric, errors='coerce')
    sequencias = Counter()
    
    for _, row in df_dezenas.iterrows():
        dezenas = sorted(row.dropna().astype(int))
        
        if len(dezenas) < 15:
            continue
            
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
            
    return pd.DataFrame(sequencias.items(), columns=["Tamanho Sequência", "Ocorrências"]).sort_values("Tamanho Sequência").reset_index(drop=True)


def analisar_combinacoes_repetidas(df):
    """Analisa a frequência das combinações de pares (duques) sorteadas."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Combinação", "Ocorrências"])

    df_dezenas = df[_colunas_dezenas(df)].apply(pd.to_numeric, errors='coerce')
    combos = Counter()
    
    for _, row in df_dezenas.iterrows():
        dezenas = sorted(row.dropna().astype(int))
        if len(dezenas) >= 15:
             combos.update(combinations(dezenas, 2))
             
    return pd.DataFrame(combos.most_common(20), columns=["Combinação", "Ocorrências"])


# ---------------------------
# Funções de Geração de Jogos
# ---------------------------

def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho=15):
    """
    Gera jogos balanceados usando estatísticas de frequência e atraso.
    """
    try:
        if tamanho < 15 or tamanho > 20:
            raise ValueError("tamanho deve estar entre 15 e 20")

        # 1. Obter Estatísticas da base limpa
        # CORREÇÃO: Chamar calcular_atrasos(df) para obter o DataFrame de atrasos
        atrasos_df = calcular_atrasos(df) 
        freq_df = calcular_frequencia(df)
        
        # Obter Top 12 Frequentes (dezenas com maior frequência)
        top_freq = freq_df.head(12)["Dezena"].tolist()

        # Obter Top 10 Atrasadas (dezenas com maior atraso atual)
        top_atraso = atrasos_df.sort_values("Atraso Atual", ascending=False)["Dezena"].head(10).tolist() 

        # 2. Geração dos Jogos
        jogos = []
        for _ in range(qtd_jogos):
            jogo = set()
            origem = {}

            # Adicionar Dezenas Frequentes (até 6)
            qtd_freq = min(6, tamanho - 5)
            for d in random.sample(top_freq, min(qtd_freq, len(top_freq))):
                jogo.add(int(d))
                origem[int(d)] = "frequente"

            # Adicionar Dezenas Atrasadas (até 4)
            qtd_atr = min(4, tamanho - len(jogo))
            candidatas_atr = [d for d in top_atraso if d not in jogo]
            for d in random.sample(candidatas_atr, min(qtd_atr, len(candidatas_atr))):
                jogo.add(int(d))
                origem[int(d)] = "atrasada"

            # Completar com números aleatórios (mantendo 1..25)
            while len(jogo) < tamanho:
                d = random.randint(1, 25)
                if d not in jogo:
                    jogo.add(d)
                    origem[d] = origem.get(d, "aleatoria")

            jogo_final = sorted(jogo)[:tamanho]
            origem_final = {d: origem.get(d, "aleatoria") for d in jogo_final}
            jogos.append((jogo_final, origem_final))

        return jogos
    except Exception as e:
        print("Erro gerar_jogos_balanceados:", e)
        return []

# ---------------------------
# Funções de Serviço e Avaliação (Simuladas/Adaptadas)
# ---------------------------

def calcular_valor_aposta(qtd_dezenas):
    """Calcula o custo da aposta."""
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)


def obter_concurso_atual_api():
    """Obtém dados do último concurso da API da Caixa (Simulação)."""
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "numero": data["numero"],
                "dataApuracao": data["dataApuracao"],
                "dezenas": [int(d) for d in data["listaDezenas"]],
            }
        return {"numero": "3513", "dataApuracao": "15/10/2025", "dezenas": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]}
    except Exception:
        return {"numero": "3513", "dataApuracao": "15/10/2025", "dezenas": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]}


def atualizar_csv_github():
    """Rotina para atualizar o CSV via API da Caixa e salvar no GitHub (Simulação)."""
    return "Função de atualização desabilitada no ambiente de demonstração."


def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    """Salva os dados do bolão em um arquivo CSV (Simulação)."""
    return f"Bolão salvo (simulação). Código: B{datetime.now().strftime('%Y%m%d')}"


def avaliar_jogos_historico(df, jogos):
    """Avalia o desempenho de um jogo no histórico (contando 11 a 15 acertos)."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Jogo", "Dezenas", "11 pts", "12 pts", "13 pts", "14 pts", "15 pts"])
        
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
    concursos = [set(row.dropna().astype(int)) for _, row in df_dezenas.iterrows() if len(row.dropna()) >= 15]
    
    jogos_list = [item[0] if isinstance(item, tuple) else item for item in jogos]
    
    linhas = []
    for idx, jogo in enumerate(jogos_list, start=1):
        cont = defaultdict(int)
        jogo_set = set(jogo)
        for sorteadas in concursos:
            acertos = len(jogo_set & sorteadas)
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


def gerar_pdf_jogos(jogos, nome="Bolão", participantes="", pix=""):
    """Gera o arquivo PDF do bolão (Simulação)."""
    # Implementação simplificada/simulada.
    return "bolao_gerado.pdf"
