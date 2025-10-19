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
from github import Github  # Depende do ambiente



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
    """Retorna lista das colunas de dezenas (índice 2 a 16)."""
    cols = list(df.columns)
    if len(cols) < 17:
        raise ValueError("DataFrame não possui colunas suficientes (esperado pelo menos 17).")
    return cols[2:17]


def calcular_atrasos(df):
    """
    Calcula:
    - Atraso Atual: concursos desde a última vez que a dezena saiu.
    - Máx Atraso: maior sequência sem sair em todo o histórico.
    Compatível com o novo CSV (Concurso, Data, Bola1..Bola15).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])

    try:
        # 1️⃣ Extrai e limpa as dezenas
        dezenas_cols = _colunas_dezenas(df)
        df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
        df_dezenas = df_dezenas.mask((df_dezenas < 1) | (df_dezenas > 25))

        # Cria lista de sets (cada linha = dezenas sorteadas no concurso)
        concursos = [set(row.dropna().astype(int).tolist()) for _, row in df_dezenas.iterrows()]
        if not concursos:
            raise ValueError("Nenhuma dezena válida foi extraída.")

        # 2️⃣ Inicializa contadores
        max_atraso = {d: 0 for d in range(1, 26)}
        atraso_atual = {d: 0 for d in range(1, 26)}
        contador = {d: 0 for d in range(1, 26)}

        # 3️⃣ Itera sobre todos os concursos (em ordem cronológica)
        for dezenas_sorteadas in concursos:
            for d in range(1, 26):
                if d in dezenas_sorteadas:
                    # Se saiu, zera o contador e registra o maior atraso
                    max_atraso[d] = max(max_atraso[d], contador[d])
                    contador[d] = 0
                else:
                    # Se não saiu, incrementa o atraso
                    contador[d] += 1

        # 4️⃣ Após percorrer tudo:
        # O contador final contém o atraso atual
        for d in range(1, 26):
            atraso_atual[d] = contador[d]
            max_atraso[d] = max(max_atraso[d], atraso_atual[d])

        # 5️⃣ Retorna DataFrame organizado
        df_out = pd.DataFrame(
            {
                "Dezena": list(range(1, 26)),
                "Máx Atraso": [max_atraso[d] for d in range(1, 26)],
                "Atraso Atual": [atraso_atual[d] for d in range(1, 26)]
            }
        ).sort_values("Atraso Atual", ascending=False).reset_index(drop=True)

        return df_out

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
    valores_limpos = pd.Series(valores)
    valores_limpos = valores_limpos[(valores_limpos >= 1) & (valores_limpos <= 25)].dropna().astype(int)
    
    contagem = Counter(valores_limpos)
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    
    todas_dezenas = pd.DataFrame({"Dezena": range(1, 26)})
    ranking = todas_dezenas.merge(ranking, on="Dezena", how="left").fillna(0)
    ranking["Frequência"] = ranking["Frequência"].astype(int)
    
    return ranking.sort_values("Frequência", ascending=False).reset_index(drop=True)



def calcular_pares_impares(df):
    """Calcula a frequência das combinações de Pares/Ímpares."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Pares", "Ímpares", "Ocorrências"])
        
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
    
    resultados = []
    for _, row in df_dezenas.iterrows():
        dezenas = row.dropna().astype(int)
        dezenas = dezenas[(dezenas >= 1) & (dezenas <= 25)]
        
        if len(dezenas) != 15:
            continue
        
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = 15 - pares
        resultados.append((pares, impares))
        
    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências").sort_values("Ocorrências", ascending=False)


def calcular_sequencias(df):
    """Calcula a frequência dos tamanhos de sequências consecutivas (2 ou mais números)."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Tamanho Sequência", "Ocorrências"])
        
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
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
            
    return pd.DataFrame(sequencias.items(), columns=["Tamanho Sequência", "Ocorrências"])\
             .sort_values("Tamanho Sequência").reset_index(drop=True)


def analisar_combinacoes_repetidas(df):
    """Analisa as combinações mais recorrentes (2 a 5 dezenas)."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return {}
    
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
    
    resultados = {}
    for tamanho in range(2, 6):  # duplas a quinas
        combos = Counter()
        for _, row in df_dezenas.iterrows():
            dezenas = sorted(row.dropna().astype(int))
            if len(dezenas) >= tamanho:
                combos.update(combinations(dezenas, tamanho))
        top5 = combos.most_common(5)
        resultados[tamanho] = pd.DataFrame(top5, columns=["Combinação", "Ocorrências"])
    
    return resultados  # dicionário: {2:df_duplas, 3:df_trincas, 4:df_quadras, 5:df_quinas}


def calcular_soma_total(df):
    """Calcula a soma total das dezenas sorteadas em cada concurso e gera estatísticas."""
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Concurso", "Soma"])
    
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
    df_soma = pd.DataFrame()
    df_soma["Concurso"] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
    df_soma["Soma"] = df_dezenas.sum(axis=1)
    
    # Estatísticas principais
    soma_min = df_soma["Soma"].min()
    soma_max = df_soma["Soma"].max()
    soma_media = df_soma["Soma"].mean()
    
    resumo = {
        "Soma Mínima": soma_min,
        "Soma Máxima": soma_max,
        "Soma Média": round(soma_media, 2)
    }
    
    return df_soma, resumo


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



def gerar_jogos_por_desempenho(df, tamanho_jogo=15, faixa_desejada=11, top_n=5):
    """
    Gera os jogos (conjuntos de dezenas) que mais vezes atingiram a faixa de acertos desejada
    nos resultados históricos da Lotofácil.
    - tamanho_jogo: 15 a 20 dezenas
    - faixa_desejada: 11 a 15
    - top_n: quantidade de melhores combinações a retornar
    """
    dezenas_cols = [c for c in df.columns if "Bola" in c or "Dezena" in c]
    if not dezenas_cols:
        raise ValueError("Não foram encontradas colunas de dezenas no arquivo CSV.")

    # Converte dezenas para numérico
    df_dezenas = df[dezenas_cols].apply(pd.to_numeric, errors='coerce')
    historico = [set(row.dropna().astype(int)) for _, row in df_dezenas.iterrows() if len(row.dropna()) >= 15]

    if not historico:
        raise ValueError("Histórico vazio ou inválido.")

    contador_combinacoes = Counter()

    # Avalia frequência de acertos
    for dezenas_sorteadas in historico:
        # Todas as combinações possíveis dentro das dezenas sorteadas com o tamanho escolhido
        if len(dezenas_sorteadas) >= tamanho_jogo:
            for combo in combinations(sorted(dezenas_sorteadas), tamanho_jogo):
                contador_combinacoes[combo] += 1

    # Agora avaliamos quantas vezes cada combinação acertaria "faixa_desejada"
    resultados = []
    for combo, _ in contador_combinacoes.items():
        acertos = {i: 0 for i in range(11, 16)}
        for dezenas_sorteadas in historico:
            intersec = len(set(combo) & dezenas_sorteadas)
            if 11 <= intersec <= 15:
                acertos[intersec] += 1
        resultados.append({
            "Jogo": combo,
            "Total": sum(acertos.values()),
            "Acertos 11": acertos[11],
            "Acertos 12": acertos[12],
            "Acertos 13": acertos[13],
            "Acertos 14": acertos[14],
            "Acertos 15": acertos[15],
            "Faixa Base": faixa_desejada,
            "Desempenho": acertos[faixa_desejada]
        })

    df_resultados = pd.DataFrame(resultados)
    df_resultados = df_resultados.sort_values("Desempenho", ascending=False).head(top_n)
    df_resultados["Jogo"] = df_resultados["Jogo"].apply(lambda x: " ".join(f"{d:02d}" for d in x))

    return df_resultados.reset_index(drop=True)






# ---------------------------
# Funções de Serviço e Avaliação (Simuladas/Adaptadas)
# ---------------------------

def calcular_valor_aposta(qtd_dezenas):
    """Calcula o custo da aposta."""
    precos = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}
    return precos.get(qtd_dezenas, 0)



def obter_concurso_atual_api():
    """
    Obtém o último concurso da Lotofácil diretamente da API oficial da Caixa.
    Retorna um dicionário padronizado com:
    {
        "numero": int,
        "dataApuracao": str (ex: "16/10/2025"),
        "dezenas": [int, int, ...]
    }
    """
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"❌ Erro HTTP {response.status_code} ao consultar API da Caixa.")
            return None

        data = response.json()

        # Segurança extra — garante que chaves existam
        numero = data.get("numero")
        data_apuracao = data.get("dataApuracao") or data.get("data") or "Data indisponível"
        dezenas = data.get("listaDezenas") or data.get("dezenasSorteadasOrdemSorteio", [])

        # Converte dezenas para inteiros
        dezenas = [int(d) for d in dezenas if str(d).isdigit()]

        return {
            "numero": numero,
            "dataApuracao": data_apuracao,
            "dezenas": dezenas
        }

    except Exception as e:
        print(f"❌ Erro ao acessar API da Caixa: {e}")
        return None

def atualizar_csv_github():
    """
    Atualiza o arquivo Lotofacil.csv (ou GitHub) com novos concursos.
    Agora salva apenas:
    Concurso, Data, Bola1...Bola15
    """
    try:
        base_url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        headers = {"accept": "application/json"}

        # 1️⃣ Obtém o último concurso disponível na API da Caixa
        response = requests.get(base_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return "❌ Erro ao acessar API da Caixa (não conseguiu obter o último concurso)."

        data = response.json()
        ultimo_disponivel = int(data["numero"])

        # 2️⃣ Obter CSV atual do GitHub
        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ Token do GitHub não encontrado. Configure GH_TOKEN como segredo."

        g = Github(token)
        repo = g.get_repo("mulequim/lotofacil")  # ✅ mantenha seu repositório aqui
        file_path = "Lotofacil_Concursos.csv"     # ✅ nome do arquivo simplificado
        contents = repo.get_contents(file_path)

        csv_data = base64.b64decode(contents.content).decode("utf-8").strip().split("\n")
        linhas = [l.split(",") for l in csv_data]

        # 3️⃣ Detecta último concurso salvo
        ultimo_no_csv = int(linhas[-1][0])
        print(f"📄 Último concurso salvo: {ultimo_no_csv} | Último disponível: {ultimo_disponivel}")

        if ultimo_no_csv >= ultimo_disponivel:
            return f"✅ Base já está atualizada até o concurso {ultimo_no_csv}."

        novos_concursos = []

        # 4️⃣ Baixa concursos faltantes um por um (em ordem)
        for numero in range(ultimo_no_csv + 1, ultimo_disponivel + 1):
            url = f"{base_url}/{numero}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"⚠️ Concurso {numero} não encontrado (pode não ter sido sorteado ainda).")
                continue

            dados = r.json()
            dezenas = [int(d) for d in dados.get("listaDezenas", [])]
            data_apuracao = dados.get("dataApuracao", "")

            nova_linha = [str(numero), data_apuracao] + [str(d) for d in dezenas]
            novos_concursos.append(nova_linha)
            print(f"✅ Concurso {numero} obtido com sucesso.")

        # 5️⃣ Atualiza arquivo no GitHub
        if not novos_concursos:
            return "⚠️ Nenhum novo concurso foi adicionado."

        linhas.extend(novos_concursos)
        novo_csv = "\n".join([",".join(l) for l in linhas])

        repo.update_file(
            path=file_path,
            message=f"Atualiza concursos até {ultimo_disponivel}",
            content=novo_csv,
            sha=contents.sha,
            branch="main"
        )

        return f"🎯 Base atualizada até o concurso {ultimo_disponivel} (adicionados {len(novos_concursos)} concursos)."

    except Exception as e:
        return f"❌ Erro ao atualizar base: {e}"




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
