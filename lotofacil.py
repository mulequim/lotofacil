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


# ---------------------------
# Salvar bolão completo (código para busca futura)
# ---------------------------
def salvar_bolao_csv(
    jogos, participantes, pix, valor_total, valor_por_pessoa,
    concurso_base=None, file_path="jogos_gerados.csv"
):
    """
    Salva o bolão (com seus jogos e dados) no repositório GitHub,
    no arquivo 'jogos_gerados.csv', sem sobrescrever o conteúdo anterior.

    Requisitos:
      - Variável de ambiente GH_TOKEN configurada
      - Repositório com permissão de escrita
    """

    try:
        # --- Configuração inicial ---
        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ Token do GitHub (GH_TOKEN) não configurado."

        g = Github(token)
        repo = g.get_repo("mulequim/lotofacil")  # 🔧 ajuste se o repositório tiver outro nome
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        codigo = f"B{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # --- Monta a linha de dados ---
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

        # --- Tenta obter o arquivo do GitHub ---
        try:
            contents = repo.get_contents(file_path)
            csv_data = base64.b64decode(contents.content).decode("utf-8").strip().split("\n")
            linhas = [l.split(",") for l in csv_data]

            # Verifica se cabeçalho está presente
            if "CodigoBolao" not in linhas[0]:
                linhas.insert(0, list(dados.keys()))

        except Exception:
            # Se o arquivo não existir ainda, cria novo
            linhas = [list(dados.keys())]

        # --- Adiciona a nova linha ---
        linhas.append([str(v) for v in dados.values()])

        # --- Reconstrói CSV ---
        novo_csv = "\n".join([",".join(l) for l in linhas])

        # --- Atualiza ou cria arquivo no GitHub ---
        if "contents" in locals():
            repo.update_file(
                path=file_path,
                message=f"Adiciona bolão {codigo}",
                content=novo_csv,
                sha=contents.sha,
                branch="main"
            )
        else:
            repo.create_file(
                path=file_path,
                message=f"Cria arquivo com bolão {codigo}",
                content=novo_csv,
                branch="main"
            )

        return codigo

    except Exception as e:
        return f"❌ Erro ao salvar bolão: {e}"


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
# Atualizar CSV local e/ou GitHub com concursos faltantes
# ---------------------------
def atualizar_csv_github():
    """
    Atualiza o arquivo Lotofacil.csv no GitHub, incluindo agora as informações
    de premiação (rateios de 11 a 15 acertos) para cada concurso.
    """
    try:
        base_url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
        headers = {"accept": "application/json"}

        # 1️⃣ Obter o último concurso disponível na API da Caixa
        response = requests.get(base_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return "❌ Erro ao acessar API da Caixa (não conseguiu obter o último concurso)."

        data = response.json()
        ultimo_disponivel = int(data["numero"])

        # 2️⃣ Obter CSV atual do GitHub
        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ Token do GitHub não encontrado. Configure o segredo GH_TOKEN."

        g = Github(token)
        repo = g.get_repo("mulequim/lotofacil")
        file_path = "Lotofacil.csv"
        contents = repo.get_contents(file_path)
        csv_data = base64.b64decode(contents.content).decode("utf-8").strip().split("\n")

        linhas = [l.split(",") for l in csv_data]
        ultimo_no_csv = int(linhas[-1][0])

        # 3️⃣ Caso o CSV já esteja atualizado
        if ultimo_no_csv >= ultimo_disponivel:
            return f"✅ Base já está atualizada (último concurso: {ultimo_disponivel})."

        novos_concursos = []
        for numero in range(ultimo_no_csv + 1, ultimo_disponivel + 1):
            url = f"{base_url}/{numero}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"⚠️ Concurso {numero} não encontrado ou ainda não disponível.")
                continue

            dados = r.json()
            dezenas = [int(d) for d in dados["listaDezenas"]]

            # --- Extrair informações de premiação ---
            rateios = {faixa["faixa"]: faixa for faixa in dados.get("listaRateioPremio", [])}
            premios = []
            for faixa in range(1, 6):  # Faixas 1 a 5 = 15 a 11 acertos
                faixa_info = rateios.get(faixa, {})
                valor = faixa_info.get("valorPremio", 0)
                ganhadores = faixa_info.get("numeroDeGanhadores", 0)
                valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                premios.extend([valor_formatado, str(ganhadores)])

            nova_linha = (
                [str(dados["numero"]), dados["dataApuracao"]] +
                [str(d) for d in dezenas] +
                premios
            )
            novos_concursos.append(nova_linha)
            print(f"✅ Concurso {numero} obtido e adicionado com premiação.")

        # 4️⃣ Atualizar CSV no GitHub
        if not novos_concursos:
            return "✅ Nenhum concurso novo encontrado."

        # --- Cabeçalho completo, com as novas colunas ---
        cabecalho = (
            ["Concurso", "Data"] +
            [f"Bola{i}" for i in range(1, 16)] +
            ["Premio15", "Ganhadores15", "Premio14", "Ganhadores14",
             "Premio13", "Ganhadores13", "Premio12", "Ganhadores12",
             "Premio11", "Ganhadores11"]
        )

        # Verifica se o cabeçalho já está no arquivo
        if "Premio15" not in linhas[0]:
            # Substitui o cabeçalho antigo por um novo completo
            linhas[0] = cabecalho

        linhas.extend(novos_concursos)
        novo_csv = "\n".join([",".join(l) for l in linhas])

        repo.update_file(
            path=file_path,
            message=f"Atualiza concursos até {ultimo_disponivel} (com premiação)",
            content=novo_csv,
            sha=contents.sha,
            branch="main"
        )

        return f"🎉 Base atualizada até o concurso {ultimo_disponivel} (adicionados {len(novos_concursos)} concursos com premiação)."

    except Exception as e:
        return f"❌ Erro ao atualizar base: {e}"




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
# Funções obter_concurso_atual_api, atualizar_csv_github, salvar_bolao_csv, gerar_pdf_jogos, e avaliar_jogos_historico
# devem ser copiadas do seu projeto original, pois o corpo delas é específico
# do seu ambiente (ex: ReportLab, requisições externas).
# Acima estão as principais funções de cálculo/estatística.
