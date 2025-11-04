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

def calcular_sequencias(df, ultimos=None):
    """
    Se ultimos=n, considera apenas os n últimos concursos para calcular sequência.
    """
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Tamanho Sequência","Ocorrências"])
    if ultimos is None or ultimos > len(df):
        df_use = df
    else:
        df_use = df.tail(ultimos)
        
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
def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho=15, seed=None,
                           penalizar_repetir_ultimo=True,
                           peso_freq=0.45, peso_atraso=0.35, peso_neutro=0.20,
                           objetivo_soma=190):
    """
    Geração balanceada de jogos (15..20).
    Melhorias:
      - penaliza sequências maiores que um limite dinâmico (mediana+1, clamp 3..6)
      - evita repetir muitas dezenas do último concurso cadastrado
      - mistura frequência + atraso + neutro por pesos
      - tenta manter soma próxima ao objetivo_soma
    Parâmetros extras:
      - penalizar_repetir_ultimo: se True evita repetir quase todas as dezenas do último sorteio
      - peso_freq, peso_atraso, peso_neutro: balanceiam seleção inicial
    Retorna: lista de (jogo_sorted_list, origem_dict)
    """

    import math
    from datetime import datetime
    random.seed(seed or int(datetime.now().timestamp()))

    if tamanho < 15 or tamanho > 20:
        raise ValueError("tamanho deve estar entre 15 e 20")

    # parâmetros ajustáveis
    MAX_ATTEMPTS_FILL = 2000  # tenta preencher evitando sequências longas
    MAX_REPEAT_LAST = max(6, tamanho - 3)  # se jogo tiver mais de MAX_REPEAT_LAST iguais ao último, evita

    # dados históricos básicos
    freq_df = calcular_frequencia(df)  # coluna 'Dezena','Frequência'
    atrasos_df = calcular_atrasos(df)  # coluna 'Dezena','Atraso Atual'

    top_freq = list(freq_df.sort_values("Frequência", ascending=False)["Dezena"].astype(int).tolist())
    top_atraso = list(atrasos_df.sort_values("Atraso Atual", ascending=False)["Dezena"].astype(int).tolist())

    # 1) limite de sequência preferido: median + 1, clamp 3..6
    seq_df = calcular_sequencias(df)
    try:
        med_seq = int(seq_df["Tamanho Sequência"].median()) if not seq_df.empty else 2
    except Exception:
        med_seq = 2
    allowed_seq = max(3, min(6, med_seq + 1))

    # 2) último concurso (se disponível) — para evitar repetições
    dezenas_cols = _colunas_dezenas(df)
    ultimo_set = set()
    if len(df) > 0:
        try:
            ultima_linha = df.iloc[-1]
            ultima = []
            for c in dezenas_cols:
                v = ultima_linha.get(c, None)
                if pd.isna(v) or v is None:
                    continue
                s = str(v).strip()
                m = re.search(r'([0-9]{1,2})', s)
                if m:
                    n = int(m.group(1))
                    if 1 <= n <= 25:
                        ultima.append(n)
            if len(ultima) >= 1:
                ultimo_set = set(ultima[:15])
        except Exception:
            ultimo_set = set()

    jogos = []
    attempts_global = 0
    while len(jogos) < qtd_jogos:
        attempts_global += 1
        if attempts_global > qtd_jogos * 50:
            # fallback: dá um break e retorna o que tem
            break

        jogo = set()
        origem = {}

        # heurística: quantidades iniciais de cada grupo proporcional ao tamanho
        n_freq = min(6, max(2, int(round(tamanho * 0.35))))
        n_atraso = min(4, max(1, int(round(tamanho * 0.25))))

        # pick por pesos (com proteção se listas curtas)
        pick_freq = random.sample(top_freq, min(n_freq, len(top_freq)))
        pick_atraso = random.sample(top_atraso, min(n_atraso, len(top_atraso)))

        for d in pick_freq:
            jogo.add(int(d)); origem[int(d)] = "quente"
        for d in pick_atraso:
            if int(d) not in jogo:
                jogo.add(int(d)); origem[int(d)] = "fria"

        # 3) Preenchimento inteligente: prioriza neutros com pequena chance para frequentes/atrasadas repetidas
        pool = [d for d in range(1, 26) if d not in jogo]
        random.shuffle(pool)

        attempts = 0
        while len(jogo) < tamanho and attempts < MAX_ATTEMPTS_FILL:
            attempts += 1
            candidate = pool.pop() if pool else random.randint(1, 25)
            if candidate in jogo:
                continue

            # avaliação rápida do impacto de adicionar candidate:
            temp = sorted(list(jogo | {candidate}))
            # calcula maior sequência do temp
            run = 1; maxrun = 1
            for i in range(1, len(temp)):
                if temp[i] == temp[i-1] + 1:
                    run += 1
                    maxrun = max(maxrun, run)
                else:
                    run = 1

            # penaliza if maxrun > allowed_seq
            if maxrun > allowed_seq:
                # probabilidade alta de pular
                if random.random() < 0.85:
                    continue

            # evita repetir *quase todas* dezenas do último concurso
            if penalizar_repetir_ultimo and ultimo_set:
                futuros = set(jogo | {candidate})
                repeats_with_last = len(futuros & ultimo_set)
                if repeats_with_last >= MAX_REPEAT_LAST:
                    # pula com alta probabilidade
                    if random.random() < 0.9:
                        continue

            # balancear soma — se soma muito distante, penaliza candidato que aumente desvio
            soma_atual = sum(jogo)
            soma_nova = soma_atual + candidate
            # expectativa final aproximada / remaining slots
            remaining = max(1, tamanho - len(jogo) - 1)
            expected_final = soma_nova + remaining * (objetivo_soma / tamanho)
            # simples penalidade
            if abs(expected_final - objetivo_soma) > 40:
                if random.random() < 0.75:
                    continue

            # ok aceita
            jogo.add(candidate)
            origem[int(candidate)] = origem.get(int(candidate), "neutra")

        # if still short, forcibly add random non-chosen numbers
        if len(jogo) < tamanho:
            for d in range(1, 26):
                if len(jogo) >= tamanho: break
                if d not in jogo:
                    jogo.add(d); origem[d] = origem.get(d, "neutra")

        # if oversize (raro) trim by quality (keep more frequent/atrasada)
        if len(jogo) > tamanho:
            sorted_keep = sorted(list(jogo),
                                 key=lambda x: ((x in top_freq) * 10 + (x in top_atraso) * 5 + random.random()),
                                 reverse=True)[:tamanho]
            jogo = set(sorted_keep)
            origem = {d: origem.get(d, "neutra") for d in jogo}

        # última validação: evitar repetição idêntica a outro já gerado
        jogo_sorted = sorted(jogo)
        if any(jogo_sorted == existing[0] for existing in jogos):
            continue

        # marca origem para as dezenas que não tinham
        for d in jogo:
            origem.setdefault(d, "neutra")

        jogos.append((jogo_sorted, origem))

    return jogos


def gerar_jogos_por_desempenho(df, tamanho_jogo=15, faixa_desejada=11, top_n=5, sample_candidates=5000, seed=None):
    """
    Mantém a heurística original mas retorna também porcentagem em relação
    ao número total de concursos avaliados.
    """
    random.seed(seed or 0)
    dezenas_cols = _colunas_dezenas(df)
    concursos = []
    for _, row in df.iterrows():
        dez = _extrair_dezenas_row(row, dezenas_cols)
        if len(dez) == 15:
            concursos.append(set(dez))
    if not concursos:
        return pd.DataFrame()

    n_concursos = len(concursos)
    results = []
    tried = set()
    for _ in range(sample_candidates):
        combo = tuple(sorted(random.sample(range(1,26), tamanho_jogo)))
        if combo in tried:
            continue
        tried.add(combo)
        acertos = Counter()
        total_hits = 0
        for sorteadas in concursos:
            hits = len(set(combo) & sorteadas)
            if hits >= 11:
                acertos[hits] += 1
                total_hits += 1
        if total_hits == 0:
            continue
        desempenho_pct = (acertos.get(faixa_desejada, 0) / n_concursos) * 100.0
        results.append({
            "Jogo": " ".join(f"{x:02d}" for x in combo),
            "Total": total_hits,
            "11": acertos.get(11,0),
            "12": acertos.get(12,0),
            "13": acertos.get(13,0),
            "14": acertos.get(14,0),
            "15": acertos.get(15,0),
            "Faixa Base": faixa_desejada,
            "Desempenho (%)": round(desempenho_pct, 6)
        })

    df_res = pd.DataFrame(sorted(results, key=lambda r: (r[f"{faixa_desejada}"], r["Total"]), reverse=True)[:top_n])
    return df_res



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
