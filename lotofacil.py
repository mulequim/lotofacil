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
# ✅ Avaliação histórica dos jogos
# ---------------------------

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

