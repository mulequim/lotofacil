"""
📘 Módulo: lotofacil.py
Autor: Marcos Oliveira
Atualizado: Outubro/2025

Funções principais usadas no app “Lotofácil Inteligente”.
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

import re
import os
import csv
import json
import uuid
import random
import base64
import requests
import pandas as pd
from collections import defaultdict
from collections import Counter
from itertools import combinations
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from github import Github  # usado apenas na função atualizar_csv_github (se necessário)


# A função carregar_dados foi mantida como a sua original, pois ela lida bem
# com a detecção de separador e limpeza inicial.
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

        # Remove colunas totalmente vazias e linhas totalmente vazias
        df = df.dropna(axis=1, how="all")
        df = df.dropna(how="all")

        # Corrige nomes se não houver "Bola1" (lógica mantida para compatibilidade)
        if not any("Bola" in c for c in df.columns):
            for i in range(1, 16):
                if f"Bola{i}" not in df.columns and i + 1 < len(df.columns):
                    df.rename(columns={df.columns[i + 1]: f"Bola{i}"}, inplace=True)

        return df

    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return None

# --- FUNÇÃO CORRIGIDA ---
def calcular_atrasos(df):
    """
    CORRIGIDA: Calcula o atraso atual e o atraso máximo de cada dezena (1..25)
    com base no histórico de concursos da Lotofácil.

    Atraso Atual = quantos concursos seguidos a dezena está sem sair
    Máx Atraso  = o maior intervalo consecutivo sem aparecer
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])

    try:
        # 1. Garantir que o DF esteja ordenado por concurso (mais antigo -> mais recente)
        concurso_col = df.columns[0] # Assume 'Concurso' é a primeira coluna
        if 'Concurso' in df.columns:
            concurso_col = 'Concurso'
        
        try:
            df[concurso_col] = pd.to_numeric(df[concurso_col], errors='coerce')
            df = df.dropna(subset=[concurso_col]).sort_values(concurso_col).reset_index(drop=True)
        except Exception:
            # Em caso de falha na ordenação, prossegue (mas idealmente deve funcionar)
            pass

        # 2. Selecionar as colunas de dezenas (índices 2 a 16) - REMOÇÃO DA LÓGICA DE DETECÇÃO COM PROBLEMAS
        # Força o uso das 15 colunas esperadas (Bola1 a Bola15)
        colunas_validas = [f"Bola{i}" for i in range(1, 16) if f"Bola{i}" in df.columns]
        
        if len(colunas_validas) != 15:
            # Se as colunas nomeadas não foram encontradas, tenta o fallback pelos índices
            colunas_validas = list(df.columns[2:17])

        if len(colunas_validas) != 15:
             raise ValueError(f"Não foi possível identificar as 15 colunas de dezenas. Encontradas {len(colunas_validas)}")

        # 3. Monta lista de concursos como conjuntos de dezenas (lógica robusta mantida)
        concursos = []
        for _, row in df.iterrows():
            dezenas = []
            for col in colunas_validas:
                val = str(row[col]).strip()
                if not val or val.lower() in ["nan", "none"]:
                    continue
                try:
                    n = int(val)
                    if 1 <= n <= 25:
                        dezenas.append(n)
                except:
                    pass
            
            # Só considera concursos onde 15 dezenas válidas foram extraídas
            if len(dezenas) == 15:
                concursos.append(set(dezenas))

        if not concursos:
            raise ValueError("Nenhum concurso válido com 15 dezenas detectado. Verifique a integridade dos dados.")

        # 4. Inicializa e calcula os atrasos (lógica mantida)
        max_atraso = {d: 0 for d in range(1, 26)}
        contador = {d: 0 for d in range(1, 26)}

        # Percorre do mais antigo → mais recente
        for sorteadas in concursos:
            for d in range(1, 26):
                if d in sorteadas:
                    # Se saiu, atualiza o máximo e zera o contador
                    max_atraso[d] = max(max_atraso[d], contador[d])
                    contador[d] = 0
                else:
                    contador[d] += 1

        # 5. Finaliza e retorna o DataFrame
        df_out = pd.DataFrame(
            [[d, max_atraso[d], contador[d]] for d in range(1, 26)], # contador[d] é o Atraso Atual
            columns=["Dezena", "Máx Atraso", "Atraso Atual"]
        )
        # O último atraso (contador[d]) também pode ser o novo Máximo
        for d in range(1, 26):
            df_out.loc[df_out["Dezena"] == d, "Máx Atraso"] = max(df_out.loc[df_out["Dezena"] == d, "Máx Atraso"].iloc[0], contador[d])
        
        return df_out.sort_values("Atraso Atual", ascending=False).reset_index(drop=True)

    except Exception as e:
        print(f"❌ Erro em calcular_atrasos: {e}")
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])

