"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Funções principais usadas no app “Lotofácil Inteligente”.
Foco na estabilidade de leitura de dezenas para cálculo de atrasos e estatísticas,
utilizando a nova base de dados Lotofacil_Concursos.csv.
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
    Lê o arquivo CSV (agora usando a base 'Lotofacil_Concursos.csv' mais limpa).
    Aplica pré-limpeza bruta nas colunas de dezenas para garantir que apenas
    dígitos sejam lidos, evitando erros de leitura.
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
# Cálculo de Atrasos (Função Central Corrigida)
# ---------------------------

def calcular_atrasos(df):
    """
    FINAL DEFINITIVA (V7): Calcula o atraso atual e o atraso máximo de cada dezena (1..25).
    Utiliza o DataFrame pré-limpo e aplica a lógica de Máximo Atraso e Atraso Atual
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
        # O DF já está limpo de sujeira, então a conversão é mais confiável.
        df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
        
        # Filtra QUALQUER número fora da faixa 1-25 (Corrige o Máx Atraso Irreal)
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
                    # Se saiu, atualiza Máximo e zera o contador
                    max_atraso[d] = max(max_atraso[d], contador[d])
                    contador[d] = 0
                else:
                    # Se não saiu, incrementa o atraso
                    contador[d] += 1

        # 3. Finaliza: O contador é o Atraso Atual
        atraso_atual = contador
        for d in range(1, 26):
             # Atualiza o Máximo Atraso, caso o Atraso Atual seja o maior da história
             max_atraso[d] = max(max_atraso[d], atraso_atual[d])

        df_out = pd.DataFrame(
            [[d, max_atraso[d], atraso_atual[d]] for d in range(1, 26)],
            columns=["Dezena", "Máx Atraso", "Atraso Atual"]
        )

        return df_out.sort_values("Atraso Atual", ascending=False).reset_index(drop=True)

    except Exception as e:
        print(f"❌ Erro em calcular_atrasos: {e}")
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])


# ---------------------------
# Funções de Suporte à Estatística
# ---------------------------

def _colunas_dezenas(df):
    """Retorna lista estrita das colunas de dezenas (índice 2 a 16)."""
    all_cols = list(df.columns)
    if len(all_cols) < 17:
        return []
    return all_cols[2:17]


def calcular_frequencia(df, ultimos=None):
    """Conta quantas vezes cada dezena saiu no período especificado."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Dezena", "Frequência"])
        
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
        
    # O DF já está pré-limpo (só contém números e NaN), facilitando a conversão
    dados = df.tail(ultimos)[dezenas_cols]
    valores = pd.to_numeric(dados.values.flatten(), errors="coerce")
    valores_limpos = pd.Series(valores).dropna().astype(int)
    
    contagem = Counter(valores_limpos)
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    
    # Garante que todas as 25 dezenas apareçam (com frequência 0 se ausentes)
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
        
        # Só conta se o concurso tiver 15 dezenas lidas corretamente
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
        
        if len(dezenas) < 15: # Ignora concursos incompletos
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
# Funções de Geração de Jogos (Ajustadas)
# ---------------------------

def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho=15):
    """
    Gera jogos balanceados usando estatísticas de frequência e atraso.
    """
    try:
        if tamanho < 15 or tamanho > 20:
            raise ValueError("tamanho deve estar entre 15 e 20")

        # 1. Obter Estatísticas da base limpa
        df_atrasos = calcular_atrasos(df)
        df_frequencia = calcular_frequencia(df)
        
        # Obter Top 12 Frequentes (dezenas com maior frequência)
        top_freq = df_frequencia.head(12)["Dezena"].tolist()

        # Obter Top 10 Atrasadas (dezenas com maior atraso atual)
        top_atraso = df_atrasos.head(10)["Dezena"].tolist()

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
# Funções de Serviço (API, PDF, Bolão - Simulações/Adaptações)
# ---------------------------

def calcular_valor_aposta(qtd_dezenas):
    """Calcula o custo da aposta."""
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)

# Funções obter_concurso_atual_api, atualizar_csv_github, salvar_bolao_csv, gerar_pdf_jogos, e avaliar_jogos_historico
# devem ser copiadas do seu projeto original, pois o corpo delas é específico
# do seu ambiente (ex: ReportLab, requisições externas).
# Acima estão as principais funções de cálculo/estatística.
