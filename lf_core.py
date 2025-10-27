"""
lotofacil.py
Versão corrigida/robusta para cálculo de atrasos, frequências, sequências,
geração de jogos e heurística de desempenho histórico.
Mantém compatibilidade com o app Streamlit fornecido.
"""

import os
import re
import random
from collections import Counter, defaultdict
from itertools import combinations
from datetime import datetime
import pandas as pd

# ---------------------------
# Carregar dados do CSV
# ---------------------------
def carregar_dados(file_path="Lotofacil_Concursos.csv"):
    """
    Lê o CSV de forma robusta. Espera que as colunas sejam:
    0: Concurso, 1: Data, 2..16: 15 dezenas (Bola1..Bola15)
    Detecta separador automaticamente (',' ou ';').
    """
    try:
        if not os.path.exists(file_path):
            print(f"[lotofacil] Arquivo não encontrado: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
        sep = ";" if sample.count(";") > sample.count(",") else ","
        df = pd.read_csv(file_path, sep=sep, engine="python", dtype=str, on_bad_lines="skip", encoding="utf-8")
        df = df.dropna(axis=1, how="all").dropna(how="all").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[lotofacil] Erro carregar_dados: {e}")
        return None

# ---------------------------
# Helpers
# ---------------------------
def _colunas_dezenas(df):
    """
    Retorna lista estrita das colunas de dezenas (índices 2 a 16) quando possível;
    se não, tenta detectar colunas com 'Bola' no nome.
    """
    if df is None:
        return []
    cols = list(df.columns)
    if len(cols) >= 17:
        return cols[2:17]
    detected = [c for c in cols if re.search(r'Bola', str(c), re.IGNORECASE)]
    return detected[:15]

def _extrair_dezenas_row(row, dezenas_cols):
    """
    Extrai até 15 dezenas válidas (1..25) de uma linha (pandas Series) usando regex.
    """
    dezenas = []
    for c in dezenas_cols:
        try:
            val = row[c]
        except Exception:
            continue
        if pd.isna(val):
            continue
        s = str(val).strip()
        m = re.search(r'([0-9]{1,2})', s)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 25:
                dezenas.append(n)
    return dezenas[:15]

# ---------------------------
# Atrasos
# ---------------------------
def calcular_atrasos(df):
    """
    Calcula Máx Atraso e Atraso Atual para dezenas 1..25.
    Assume que df pode ser ordenado por 'Concurso' (faz tentativa).
    """
    try:
        if df is None or df.empty:
            return pd.DataFrame(columns=["Dezena", "Máx Atraso", "Atraso Atual"])

        # tenta ordenar por 'Concurso' se existir
        if "Concurso" in df.columns:
            try:
                df["Concurso"] = pd.to_numeric(df["Concurso"], errors="coerce")
                df = df.dropna(subset=["Concurso"]).sort_values("Concurso").reset_index(drop=True)
            except Exception:
                pass

        dezenas_cols = _colunas_dezenas(df)
        concursos = []
        for _, row in df.iterrows():
            dez = _extrair_dezenas_row(row, dezenas_cols)
            if len(dez) == 15:
                concursos.append(set(dez))

        if not concursos:
            return pd.DataFrame([[d,0,0] for d in range(1,26)], columns=["Dezena","Máx Atraso","Atraso Atual"])

        max_atraso = {d:0 for d in range(1,26)}
        contador = {d:0 for d in range(1,26)}

        # do mais antigo para o mais recente
        for sorteadas in concursos:
            for d in range(1,26):
                if d in sorteadas:
                    max_atraso[d] = max(max_atraso[d], contador[d])
                    contador[d] = 0
                else:
                    contador[d] += 1

        atraso_atual = contador
        for d in range(1,26):
            max_atraso[d] = max(max_atraso[d], atraso_atual[d])

        df_out = pd.DataFrame([[d, max_atraso[d], atraso_atual[d]] for d in range(1,26)],
                              columns=["Dezena","Máx Atraso","Atraso Atual"])
        return df_out.sort_values("Atraso Atual", ascending=False).reset_index(drop=True)
    except Exception as e:
        print(f"[lotofacil] Erro calcular_atrasos: {e}")
        return pd.DataFrame(columns=["Dezena","Máx Atraso","Atraso Atual"])

# ---------------------------
# Frequência
# ---------------------------
def calcular_frequencia(df, ultimos=None):
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Dezena","Frequência"])
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
    dados = df.tail(ultimos)[dezenas_cols]
    valores = pd.Series(pd.to_numeric(dados.values.flatten(), errors="coerce")).dropna().astype(int)
    cont = Counter(valores)
    todos = pd.DataFrame({"Dezena": list(range(1,26))})
    freq = pd.DataFrame(cont.most_common(), columns=["Dezena","Frequência"])
    freq["Dezena"] = freq["Dezena"].astype(int)
    merged = todos.merge(freq, on="Dezena", how="left").fillna(0)
    merged["Frequência"] = merged["Frequência"].astype(int)
    return merged.sort_values("Frequência", ascending=False).reset_index(drop=True)

# ---------------------------
# Pares / Ímpares
# ---------------------------
def calcular_pares_impares(df):
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Pares","Ímpares","Ocorrências"])
    df_dez = df[dezenas_cols].apply(lambda col: pd.to_numeric(col, errors='coerce'))
    resultados = []
    for _, row in df_dez.iterrows():
        nums = row.dropna().astype(int)
        if len(nums) != 15:
            continue
        pares = sum(1 for n in nums if n % 2 == 0)
        impares = 15 - pares
        resultados.append((pares, impares))
    df_stats = pd.DataFrame(resultados, columns=["Pares","Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")

# ---------------------------
# Sequências
# ---------------------------
def calcular_sequencias(df):
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(columns=["Tamanho Sequência","Ocorrências"])
    df_dez = df[dezenas_cols].apply(lambda col: pd.to_numeric(col, errors='coerce'))
    seqs = Counter()
    for _, row in df_dez.iterrows():
        nums = sorted(set(row.dropna().astype(int).tolist()))
        if len(nums) < 2:
            continue
        cur = 1
        for i in range(1, len(nums)):
            if nums[i] == nums[i-1] + 1:
                cur += 1
            else:
                if cur >= 2:
                    seqs[cur] += 1
                cur = 1
        if cur >= 2:
            seqs[cur] += 1
    return pd.DataFrame(seqs.items(), columns=["Tamanho Sequência","Ocorrências"]).sort_values("Tamanho Sequência").reset_index(drop=True)

# ---------------------------
# Combinações Repetidas (2..5)
# ---------------------------
def analisar_combinacoes_repetidas(df, top_n_each=5):
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return {}
    df_dez = df[dezenas_cols].apply(lambda col: pd.to_numeric(col, errors='coerce'))
    combos = Counter()
    for _, row in df_dez.iterrows():
        nums = sorted(set(row.dropna().astype(int).tolist()))
        if len(nums) < 2:
            continue
        for k in range(2,6):
            if len(nums) >= k:
                combos.update(combinations(nums, k))
    results = {}
    for k in range(2,6):
        sub = [(c,v) for c,v in combos.items() if len(c)==k]
        sub_sorted = sorted(sub, key=lambda x: x[1], reverse=True)[:top_n_each]
        results[k] = pd.DataFrame([(' '.join(f"{x:02d}" for x in combo), cnt) for combo,cnt in sub_sorted],
                                  columns=["Combinação","Ocorrências"])
    return results

# ---------------------------
# Gerar jogos balanceados
# ---------------------------
def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho=15, seed=None):
    """
    Gera jogos balanceados. Penaliza sequências maiores que um limite calculado
    pela mediana da distribuição histórica (inteligente).
    Retorna lista de (jogo_sorted_list, origem_dict).
    """
    random.seed(seed or int(datetime.now().timestamp()))
    if tamanho < 15 or tamanho > 20:
        raise ValueError("tamanho deve estar entre 15 e 20")

    freq_df = calcular_frequencia(df)
    atrasos_df = calcular_atrasos(df)
    top_freq = list(freq_df.sort_values("Frequência", ascending=False)["Dezena"].astype(int).tolist())
    top_atraso = list(atrasos_df.sort_values("Atraso Atual", ascending=False)["Dezena"].astype(int).tolist())

   

# limite de sequência preferido: median+1, clamp 3..6
    seq_df = calcular_sequencias(df)
    med_seq = int(seq_df["Tamanho Sequência"].median()) if not seq_df.empty else 2
    allowed_seq = max(3, min(6, med_seq + 1))

    jogos = []
    for _ in range(qtd_jogos):
        jogo = set()
        origem = {}

        # heurísticas de quantidades
        n_freq = min(6, max(3, tamanho//3))
        n_atraso = min(4, max(2, tamanho//6))

        # adicionar frequentes
        chosen_freq = random.sample(top_freq, min(n_freq, len(top_freq)))
        for d in chosen_freq:
            jogo.add(int(d)); origem[int(d)] = "quente"

        # adicionar atrasadas
        chosen_atr = random.sample(top_atraso, min(n_atraso, len(top_atraso)))
        for d in chosen_atr:
            if d not in jogo:
                jogo.add(int(d)); origem[int(d)] = "fria"

        # completar evitando sequências longas
        pool = [d for d in range(1,26) if d not in jogo]
        random.shuffle(pool)
        for candidate in pool:
            if len(jogo) >= tamanho:
                break
            temp = sorted(list(jogo | {candidate}))
            run = 1; maxrun = 1
            for i in range(1, len(temp)):
                if temp[i] == temp[i-1] + 1:
                    run += 1; maxrun = max(maxrun, run)
                else:
                    run = 1
            if maxrun > allowed_seq:
                # forte probabilidade de pular
                if random.random() < 0.85:
                    continue
            jogo.add(candidate); origem[int(candidate)] = origem.get(int(candidate), "neutra")

        # ajustar tamanho exato
        if len(jogo) > tamanho:
            jogo = set(sorted(jogo)[:tamanho])
        elif len(jogo) < tamanho:
            for d in range(1,26):
                if len(jogo) >= tamanho: break
                if d not in jogo:
                    jogo.add(d); origem[d] = origem.get(d, "neutra")

        jogos.append((sorted(jogo), origem))
    return jogos

# ---------------------------
# Gerar jogos por desempenho histórico (heurística)
# ---------------------------
def gerar_jogos_por_desempenho(df, tamanho_jogo=15, faixa_desejada=11, top_n=5, sample_candidates=5000, seed=None):
    """
    Heurística: amostra muitas combinações aleatórias e avalia quantas vezes
    cada combinação atingiu a faixa desejada (11..15). Retorna top_n melhores.
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
# Soma total das dezenas
# ---------------------------
def calcular_soma_total(df):
    dezenas_cols = _colunas_dezenas(df)
    if not dezenas_cols:
        return pd.DataFrame(), {"Soma Mínima":0,"Soma Média":0,"Soma Máxima":0}
    listas = []
    for _, row in df.iterrows():
        nums = _extrair_dezenas_row(row, dezenas_cols)
        if len(nums) == 15:
            listas.append((row.get("Concurso", ""), sum(nums)))
    df_soma = pd.DataFrame(listas, columns=["Concurso","Soma"])
    resumo = {
        "Soma Mínima": int(df_soma["Soma"].min() if not df_soma.empty else 0),
        "Soma Média": float(df_soma["Soma"].mean() if not df_soma.empty else 0.0),
        "Soma Máxima": int(df_soma["Soma"].max() if not df_soma.empty else 0)
    }
    return df_soma, resumo

# ---------------------------
# Avaliação histórica de jogos
# ---------------------------
def avaliar_jogos_historico(df, jogos):
    dezenas_cols = _colunas_dezenas(df)
    concursos = []
    for _, row in df.iterrows():
        dez = _extrair_dezenas_row(row, dezenas_cols)
        if len(dez) == 15:
            concursos.append(set(dez))
    linhas = []
    for idx, item in enumerate(jogos, start=1):
        if isinstance(item, (list, tuple)) and isinstance(item[0], (list, tuple)):
            jogo = item[0]
        else:
            jogo = item if isinstance(item, (list, tuple)) else []
        jogo_set = set(int(x) for x in jogo)
        cont = Counter()
        for s in concursos:
            hits = len(jogo_set & s)
            if hits >= 11:
                cont[hits] += 1
        linhas.append({
            "Jogo": idx,
            "Dezenas": " ".join(f"{d:02d}" for d in sorted(jogo)),
            "11 pts": cont.get(11,0),
            "12 pts": cont.get(12,0),
            "13 pts": cont.get(13,0),
            "14 pts": cont.get(14,0),
            "15 pts": cont.get(15,0),
        })
    return pd.DataFrame(linhas)




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
