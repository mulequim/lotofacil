import pandas as pd
from github import Github
import requests
import base64
import os
import random
import csv
import json
import uuid
from collections import Counter
from itertools import combinations
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime


# ---------------------------
# Carregar dados do CSV
# ---------------------------
def carregar_dados(file_path="Lotofacil.csv"):
    """
    Carrega o CSV local (ou atualizado do GitHub) e garante compatibilidade com
    os novos campos de premiação.
    """
    try:
        df = pd.read_csv(file_path, sep=",")
        dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
        if not all(c in df.columns for c in dezenas_cols):
            raise ValueError("Colunas de dezenas ausentes no CSV.")

        # Adiciona colunas de premiação se não existirem
        for col in [
            "Premio15", "Ganhadores15", "Premio14", "Ganhadores14",
            "Premio13", "Ganhadores13", "Premio12", "Ganhadores12",
            "Premio11", "Ganhadores11"
        ]:
            if col not in df.columns:
                df[col] = None

        return df
    except Exception as e:
        print("❌ Erro ao carregar dados:", e)
        return None


# ---------------------------
# Frequência de dezenas
# ---------------------------
def calcular_frequencia(df, ultimos=None):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    if ultimos is None or ultimos > len(df):
        ultimos = len(df)
    dados = df.tail(ultimos)[dezenas_cols]
    contagem = Counter(dados.values.flatten())
    ranking = pd.DataFrame(contagem.most_common(), columns=["Dezena", "Frequência"])
    return ranking


# ---------------------------
# Atrasos
# ---------------------------
def calcular_atrasos(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    max_atrasos = {d: 0 for d in range(1, 26)}
    atual_atraso = {d: 0 for d in range(1, 26)}

    for _, row in df[::-1].iterrows():
        sorteadas = set(row[dezenas_cols].values)
        for d in range(1, 26):
            if d not in sorteadas:
                atual_atraso[d] += 1
            else:
                max_atrasos[d] = max(max_atrasos[d], atual_atraso[d])
                atual_atraso[d] = 0

    dados = [[d, max_atrasos[d], atual_atraso[d]] for d in range(1, 26)]
    return pd.DataFrame(dados, columns=["Dezena", "Máx Atraso", "Atraso Atual"])


# ---------------------------
# Pares e Ímpares
# ---------------------------
def calcular_pares_impares(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    resultados = []

    for _, row in df.iterrows():
        dezenas = row[dezenas_cols].values
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = 15 - pares
        resultados.append((pares, impares))

    df_stats = pd.DataFrame(resultados, columns=["Pares", "Ímpares"])
    return df_stats.value_counts().reset_index(name="Ocorrências")


# ---------------------------
# Sequências
# ---------------------------
def calcular_sequencias(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    sequencias = Counter()

    for _, row in df.iterrows():
        dezenas = sorted(row[dezenas_cols].values)
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

    df_seq = pd.DataFrame(sequencias.items(), columns=["Tamanho Sequência", "Ocorrências"])
    return df_seq.sort_values("Tamanho Sequência")


# ---------------------------
# Combinações mais recorrentes
# ---------------------------
def analisar_combinacoes_repetidas(df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    combos_contagem = {"Pares": Counter(), "Trios": Counter(), "Quartetos": Counter()}

    for _, row in df.iterrows():
        dezenas = sorted(map(int, row[dezenas_cols].values))
        combos_contagem["Pares"].update(combinations(dezenas, 2))
        combos_contagem["Trios"].update(combinations(dezenas, 3))
        combos_contagem["Quartetos"].update(combinations(dezenas, 4))

    resultado = []
    for tipo, contagem in combos_contagem.items():
        for combo, freq in contagem.most_common(5):
            resultado.append({"Tipo": tipo, "Combinação": combo, "Ocorrências": freq})

    return pd.DataFrame(resultado)


# ---------------------------
# Gerar jogos balanceados
# ---------------------------
def gerar_jogos_balanceados(df, qtd_jogos=4, tamanho_jogo=15):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]

    # Frequentes
    freq = calcular_frequencia(df)
    top_frequentes = freq.head(10)["Dezena"].tolist()

    # Atrasadas
    atrasos = calcular_atrasos(df)
    top_atrasadas = atrasos.sort_values("Atraso Atual", ascending=False).head(5)["Dezena"].tolist()

    # Combinações mais comuns
    todas_combs = Counter()
    for _, row in df.iterrows():
        dezenas = sorted(row[dezenas_cols].values)
        for comb in combinations(dezenas, 3):
            todas_combs[comb] += 1
    trios_flat = list(set([n for trio, _ in todas_combs.most_common(5) for n in trio]))

    pares = [d for d in range(1, 26) if d % 2 == 0]
    impares = [d for d in range(1, 26) if d % 2 != 0]

    jogos = []
    for _ in range(qtd_jogos):
        jogo = set()
        origem = {}

        # Frequentes
        for d in random.sample(top_frequentes, min(6, len(top_frequentes))):
            jogo.add(d)
            origem[d] = "frequente"

        # Atrasadas
        for d in random.sample(top_atrasadas, min(3, len(top_atrasadas))):
            if d not in jogo:
                jogo.add(d)
                origem[d] = "atrasada"

        # Recorrentes
        for d in random.sample(trios_flat, min(3, len(trios_flat))):
            if d not in jogo:
                jogo.add(d)
                origem[d] = "repetida"

        # Completar
        while len(jogo) < tamanho_jogo:
            grupo = pares if len([x for x in jogo if x % 2 != 0]) > 7 else impares
            d = random.choice(grupo)
            if d not in jogo:
                jogo.add(d)
                origem[d] = "equilibrio"

        jogos.append((sorted(jogo), origem))

    return jogos


# ---------------------------
# Avaliar jogos
# ---------------------------
def avaliar_jogos(jogos, df):
    dezenas_cols = [f"Bola{i}" for i in range(1, 16)]
    resultados = []

    for idx, (jogo, origem) in enumerate(jogos, start=1):
        contagens = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        for _, row in df.iterrows():
            acertos = len(set(row[dezenas_cols].values) & set(jogo))
            if acertos >= 11:
                contagens[acertos] += 1
        resultados.append((idx, jogo, contagens))

    return resultados


# ---------------------------
# Valor da aposta
# ---------------------------
def calcular_valor_aposta(qtd_dezenas):
    precos = {
        15: 3.50,
        16: 56.00,
        17: 476.00,
        18: 2856.00,
        19: 13566.00,
        20: 54264.00
    }
    return precos.get(qtd_dezenas, 0)


# ---------------------------
# Geração de PDF
# ---------------------------
def gerar_pdf_jogos(jogos, nome="Loteria", participantes="", pix=""):
    """Gera um PDF com os jogos e resumo financeiro."""
    # Preparar dados financeiros
    participantes_lista = [p.strip() for p in participantes.split(",") if p.strip()]
    num_participantes = len(participantes_lista) if participantes_lista else 1

    valor_total = sum(calcular_valor_aposta(len(jogo)) for jogo, _ in jogos)
    valor_por_pessoa = valor_total / num_participantes if num_participantes > 0 else valor_total

    file_name = f"jogos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    largura, altura = A4
    y = altura - 2 * cm

    # Cabeçalho
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, f"🎯 Bolão Lotofácil - {nome}")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 1 * cm

    # Participantes e PIX
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "👥 Participantes:")
    y -= 0.4 * cm
    c.setFont("Helvetica", 10)
    if participantes_lista:
        for p in participantes_lista:
            c.drawString(2.5 * cm, y, f"- {p}")
            y -= 0.4 * cm
    else:
        c.drawString(2.5 * cm, y, "Nenhum participante informado.")
        y -= 0.5 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, f"💸 PIX para pagamento: {pix if pix else 'Não informado'}")
    y -= 1 * cm

    # Resumo financeiro
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "📊 Resumo Financeiro:")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * cm, y, f"Total de Jogos: {len(jogos)}")
    y -= 0.4 * cm
    c.drawString(2.5 * cm, y, f"Valor Total da Aposta: R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 0.4 * cm
    c.drawString(2.5 * cm, y, f"Número de Participantes: {num_participantes}")
    y -= 0.4 * cm
    c.drawString(2.5 * cm, y, f"Valor por Participante: R$ {valor_por_pessoa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 1 * cm

    # Listagem dos jogos
    for i, (jogo, origem) in enumerate(jogos, start=1):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"🎲 Jogo {i} ({len(jogo)} dezenas)")
        y -= 0.6 * cm
        c.setFont("Helvetica", 11)
        dezenas_str = "  ".join([str(d).zfill(2) for d in jogo])
        c.drawString(2.5 * cm, y, dezenas_str)
        y -= 0.7 * cm

        valor = calcular_valor_aposta(len(jogo))
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(2.5 * cm, y, f"💰 Valor: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 0.9 * cm

        if y < 4 * cm:
            c.showPage()
            y = altura - 3 * cm

    c.save()
    return file_name



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
# ---------------------------
# Salvar Jogos
# ---------------------------

def salvar_bolao_csv(jogos, participantes, pix, valor_total, valor_por_pessoa, concurso_base=None, file_path="jogos_gerados.csv"):
    """
    Salva as informações do bolão em um arquivo CSV local.
    Retorna o código único do bolão.
    """
    codigo = f"B{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    dados = {
        "CodigoBolao": codigo,
        "DataHora": data_hora,
        "Participantes": participantes,
        "Pix": pix,
        "QtdJogos": len(jogos),
        "ValorTotal": round(valor_total, 2),
        "ValorPorPessoa": round(valor_por_pessoa, 2),
        "Jogos": json.dumps([j for j, _ in jogos]),  # salva os jogos como texto JSON
        "ConcursoBase": concurso_base or ""
    }

    # Se o arquivo não existir, cria com cabeçalho
    try:
        criar_cabecalho = not os.path.exists(file_path)
        with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=dados.keys())
            if criar_cabecalho:
                writer.writeheader()
            writer.writerow(dados)
        return codigo
    except Exception as e:
        print(f"❌ Erro ao salvar bolão: {e}")
        return None

        

        return f"🎉 Base atualizada até o concurso {ultimo_disponivel} (adicionados {len(novos_concursos)} concursos com premiação)."

    except Exception as e:
        return f"❌ Erro ao atualizar base: {e}"
