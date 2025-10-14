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
"""
def _detectar_colunas_dezenas(df):
    
    Tenta detectar automaticamente as 15 colunas que contém as dezenas.
    Estratégia:
      - procura colunas cujo maior número inteiro encontrado esteja entre 1 e 25
      - escolhe as 15 primeiras colunas que satisfazem (ou, se não encontrar,
        assume colunas na posição 2..16 como fallback)
    Retorna lista de nomes de colunas.
    
    candidato = []
    for col in df.columns:
        # converte em séries numéricas (coerce -> NaN para não-numéricos)
        serie = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors="coerce")
        # percentagem de valores válidos e se os valores estão no intervalo 1..25
        validos = serie.dropna()
        if len(validos) == 0:
            continue
        vmax = validos.max()
        vmin = validos.min()
        pct_valid = len(validos) / len(serie)
        if 1 <= vmin <= 25 and 1 <= vmax <= 25 and pct_valid >= 0.6:
            candidato.append(col)
    # se encontrou pelo menos 15, pega as 15 mais prováveis
    if len(candidato) >= 15:
        return candidato[:15]
    # fallback: tenta usar colunas que contenham 'Bola' no nome
    bolas = [c for c in df.columns if "Bola" in c or "bola" in c.lower()]
    if len(bolas) >= 15:
        return bolas[:15]
    # fallback final: colunas 3..17 (índice 2..16) — comum em CSVs (Concurso,Data,Bola1..)
    all_cols = list(df.columns)
    if len(all_cols) >= 17:
        return all_cols[2:17]
    # se tudo falhar, retorna as primeiras 15 colunas disponíveis (defensivo)
    return all_cols[:15]


def (df):
    
    Calcula para cada dezena (1..25):
      - Máx Atraso: maior sequência consecutiva de concursos em que a dezena NÃO saiu (em todo o histórico)
      - Atraso Atual: sequência consecutiva desde o concurso mais recente até o primeiro concurso anterior que a dezena apareceu
      - (opcional) Última aparição: índice/posição do último concurso onde a dezena apareceu (pode ser usado para mostrar 'desde o concurso N')

    Retorna DataFrame com colunas:
      ['Dezena', 'Máx Atraso', 'Atraso Atual', 'UltimaAparicaoIndice']

    Observações:
      - A função detecta automaticamente as colunas de dezenas.
      - Trabalha de forma robusta com valores sujos (faz coercion para int).
    
    # Detecta colunas de dezenas
    dezenas_cols = _detectar_colunas_dezenas(df)
    # Constrói lista ordenada de sorteios (cada elemento é set de dezenas) em ordem cronológica (antigo -> recente)
    draws = []
    for _, row in df.iterrows():
        # extrai e converte as dezenas daquela linha
        valores = pd.to_numeric(row[dezenas_cols].astype(str).str.extractall(r'(\d+)')[0], errors="coerce")
        # alternativa: tentar converter diretamente e dropar NaNs
        try:
            nums = pd.to_numeric(row[dezenas_cols], errors="coerce").dropna().astype(int).tolist()
        except Exception:
            nums = [int(x) for x in row[dezenas_cols].astype(str).str.extractall(r'(\d+)')[0].dropna().astype(int).tolist()]
        # filtra apenas 1..25
        nums = [int(n) for n in nums if 1 <= int(n) <= 25]
        draws.append(set(nums))

    n_draws = len(draws)
    # Prepara estruturas de resultado
    max_atrasos = {d: 0 for d in range(1, 26)}
    atraso_atual = {d: 0 for d in range(1, 26)}
    ultima_aparicao_idx = {d: None for d in range(1, 26)}  # índice do draw (0..n-1) da última aparição

    # Calcula Última Aparição (varre do mais recente para o antigo e grava primeiro encontro)
    for idx in range(n_draws - 1, -1, -1):
        sorteadas = draws[idx]
        for d in range(1, 26):
            if ultima_aparicao_idx[d] is None and d in sorteadas:
                ultima_aparicao_idx[d] = idx  # índice da última aparição

    # Calcula Atraso Atual: contar a partir do último sorteio (n_draws-1) indo para trás até encontrar a dezena
    for d in range(1, 26):
        cont = 0
        # percorre do último concurso para o primeiro até encontrar a dezena
        for idx in range(n_draws - 1, -1, -1):
            if d in draws[idx]:
                break
            cont += 1
        atraso_atual[d] = cont

    # Calcula Máx Atraso: varre toda a série e mede os blocos consecutivos sem a dezena
    for d in range(1, 26):
        maior = 0
        atual = 0
        for idx in range(n_draws):
            if d not in draws[idx]:
                atual += 1
            else:
                if atual > maior:
                    maior = atual
                atual = 0
        # caso a maior sequência esteja no final (não fechou com aparição), compara novamente
        if atual > maior:
            maior = atual
        max_atrasos[d] = maior

    # Monta DataFrame de saída
    linhas = []
    for d in range(1, 26):
        ua = ultima_aparicao_idx[d]
        # opcional: converte índice para posição de concurso ou deixa índice; aqui deixamos índice (0=primeiro registro)
        linhas.append({
            "Dezena": d,
            "Máx Atraso": int(max_atrasos[d]),
            "Atraso Atual": int(atraso_atual[d]),
            "UltimaAparicaoIndice": ua if ua is not None else ""
        })

    df_res = pd.DataFrame(linhas)
    return df_res.sort_values("Atraso Atual", ascending=False).reset_index(drop=True)
"""

 
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
        atrasos_df = (df)
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

def avaliar_jogos_historico(df, jogos):
    """
    Avalia cada jogo (lista de dezenas) comparando com o histórico de concursos (df).
    Conta quantas vezes o jogo teria feito 11, 12, 13, 14 ou 15 acertos.

    Parâmetros:
        df (pd.DataFrame): DataFrame com o histórico (pode conter colunas extras).
        jogos: lista onde cada item é:
               - uma lista/tupla de dezenas [1,2,3,...]
               - ou (jogo, origem) como seu gerador produz [( [..], {...} ), ...]

    Retorna:
        pd.DataFrame com colunas ["Jogo", "Dezenas", "11 pts", "12 pts", "13 pts", "14 pts", "15 pts"]
    """

    # 1) Detectar automaticamente colunas de dezenas (melhor esforço)
    # Critério: coluna que, em boa parte das linhas, contém inteiros entre 1 e 25.
    possíveis = []
    n_linhas = min(50, len(df)) if len(df) > 0 else 0

    for col in df.columns:
        sucesso = 0
        total = 0
        for _, row in df.head(n_linhas).iterrows():
            val = row[col]
            if pd.isna(val):
                continue
            s = str(val).strip()
            # tenta converter direto
            try:
                v = int(re.sub(r'\D', '', s)) if re.search(r'\d', s) else None
                if v is not None and 1 <= v <= 25:
                    sucesso += 1
            except:
                pass
            total += 1
        # se a coluna tem boa taxa de valores 1..25, considera
        if total > 0 and (sucesso / total) >= 0.5:
            possíveis.append(col)

    # Ordena por posição original das colunas e pega até 15
    possíveis = sorted(possíveis, key=lambda c: list(df.columns).index(c))
    dezenas_cols = possíveis[:15]

    # Se não detectou, tenta fallback simples: usar as colunas 2..16 (como muitos CSVs têm formato)
    if len(dezenas_cols) < 15:
        fallback = list(df.columns)[2:17]
        dezenas_cols = fallback if len(fallback) >= 15 else dezenas_cols

    # 2) Monta lista de conjuntos (cada concurso -> set de 15 dezenas)
    concursos = []
    for _, row in df.iterrows():
        dezenas_row = []
        # tenta primeiro pelas colunas detectadas
        for col in dezenas_cols:
            try:
                val = row[col]
                if pd.isna(val):
                    continue
                s = str(val).strip()
                # extrai número se houver ruído (ex: "R$ 1.234,00" -> 123400 não é dezena,
                # mas se a célula for "01" ou "1" ou " 1 " ou "03" etc, será convertido)
                # melhor tentar extrair dígitos curtos com regex de 1-2 chars
                m = re.search(r'\b([0-9]{1,2})\b', s)
                if m:
                    v = int(m.group(1))
                    if 1 <= v <= 25:
                        dezenas_row.append(v)
                else:
                    # como fallback, tentar converter inteiro direto
                    try:
                        v = int(s)
                        if 1 <= v <= 25:
                            dezenas_row.append(v)
                    except:
                        pass
            except Exception:
                continue

        # Se não achou 15 dezenas nas colunas detectadas, tenta extrair quaisquer números na linha inteira
        if len(dezenas_row) < 15:
            linha_concat = " ".join(str(x) for x in row.values)
            achados = re.findall(r'\b([0-9]{1,2})\b', linha_concat)
            dezenas_row = [int(x) for x in achados if 1 <= int(x) <= 25][:15]

        if len(dezenas_row) == 15:
            concursos.append(set(dezenas_row))
        # caso não consiga extrair 15 dezenas, ignora essa linha (evita falsos positivos)

    # 3) Normalizar entrada 'jogos' para lista de listas de inteiros
    jogos_list = []
    for item in jogos:
        if isinstance(item, (list, tuple)) and len(item) > 0 and isinstance(item[0], (list, tuple, set)):
            # formato (jogo, origem) -> pega item[0]
            jogo = item[0]
        elif isinstance(item, (list, tuple, set)) and (all(isinstance(x, int) or (isinstance(x, str) and x.isdigit()) for x in item)):
            jogo = item
        else:
            # formato inesperado: tenta extrair números com regex
            s = str(item)
            nums = re.findall(r'\b([0-9]{1,2})\b', s)
            jogo = [int(x) for x in nums]
        # garantir inteiros
        jogo_ints = [int(x) for x in jogo]
        jogos_list.append(sorted(set([d for d in jogo_ints if 1 <= d <= 25])))

    # 4) Para cada jogo, contar ocorrências de 11..15
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



